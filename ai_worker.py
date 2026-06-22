import os
import json
import logging
import re
import time
import requests
import pika
from dotenv import load_dotenv
from transformers import pipeline
from services.text_extraction import TextExtractionService

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai_worker")

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
SPRING_BOOT_CALLBACK_URL = os.getenv('SPRING_BOOT_CALLBACK_URL', 'http://localhost:8080')
MODEL_ID = os.getenv('HF_MODEL_ID', 'Hello-SimpleAI/chatgpt-detector-roberta')
QUEUE_NAME = "ai.detection.queue"

logger.info(f"Initializing AI Worker | Host: {RABBITMQ_HOST} | Callback URL: {SPRING_BOOT_CALLBACK_URL}")

# Load model once at startup
logger.info(f"Loading local transformer model: '{MODEL_ID}'...")
try:
    classifier = pipeline(
        "text-classification",
        model=MODEL_ID,
        tokenizer=MODEL_ID,
        top_k=None,
        device=-1  # Force CPU
    )
    logger.info("Local model loaded successfully.")
except Exception as e:
    logger.critical(f"Failed to load local model: {str(e)}")
    classifier = None

def chunk_text(text: str, max_words: int = 220, overlap: int = 30) -> list:
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    step = max_words - overlap
    for start in range(0, len(words), step):
        chunk_words = words[start:start + max_words]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if start + max_words >= len(words):
            break
    return chunks

def parse_classifier_output(predictions) -> dict:
    ai_score = 0.0
    human_score = 0.0
    for pred in predictions:
        label = pred.get('label', '').lower()
        score = pred.get('score', 0.0) * 100
        if 'human' in label or 'written' in label or label == 'label_0':
            human_score = max(human_score, score)
        else:
            ai_score = max(ai_score, score)
            
    total = ai_score + human_score
    if total > 0:
        ai_score = (ai_score / total) * 100
        human_score = (human_score / total) * 100
        
    confidence = max(ai_score, human_score) / 100
    label = "AI-generated" if ai_score >= 50 else "Human-written"
    
    return {
        "ai_score": ai_score,
        "human_score": human_score,
        "confidence": confidence,
        "label": label
    }

def send_callback(submission_id, score):
    url = f"{SPRING_BOOT_CALLBACK_URL}/internal/submissions/{submission_id}/ai-result"
    payload = {"score": score}
    headers = {"Content-Type": "application/json"}
    try:
        logger.info(f"Sending callback to {url} with score: {score}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        logger.info(f"Callback status code: {response.status_code} | Response: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send callback for submission {submission_id}: {str(e)}")

def process_message(ch, method, properties, body):
    try:
        logger.info(f"Processing new message...")
        body_str = body.decode('utf-8', errors='ignore').strip()
        
        submission_id = None
        text = None
        
        # Check if the payload is JSON
        try:
            data = json.loads(body_str)
            if isinstance(data, dict):
                submission_id = data.get("submissionId") or data.get("submission_id")
                text = data.get("text")
        except json.JSONDecodeError:
            # If not JSON, check if it matches a UUID pattern (raw submissionId from Java)
            if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', body_str, re.IGNORECASE):
                submission_id = body_str
            else:
                logger.error(f"Unparseable message payload: {body_str}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

        if not submission_id:
            logger.error(f"Failed to retrieve submissionId from payload: {body_str}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # If text is not supplied in message, download file from Spring Boot
        if not text:
            logger.info(f"Downloading file for submission ID: {submission_id}")
            download_url = f"{SPRING_BOOT_CALLBACK_URL}/api/submissions/{submission_id}/download"
            try:
                response = requests.get(download_url, timeout=30)
                if response.status_code != 200:
                    logger.error(f"Download failed for submission {submission_id} (HTTP {response.status_code})")
                    send_callback(submission_id, 0.0)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
                
                # Retrieve filename from Content-Disposition
                file_name = "submission.txt"
                content_disp = response.headers.get('Content-Disposition', '')
                filename_match = re.search(r'filename="?([^";]+)"?', content_disp)
                if filename_match:
                    file_name = filename_match.group(1)
                
                # Extract text using TextExtractionService
                text = TextExtractionService.extract_from_bytes(response.content, file_name)
                logger.info(f"Successfully extracted {len(text.split())} words from '{file_name}'")
            except Exception as e:
                logger.error(f"Error fetching/extracting text for submission {submission_id}: {str(e)}")
                send_callback(submission_id, 0.0)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

        if not text or len(text.strip()) == 0:
            logger.warn(f"No text extracted or text is empty for submission {submission_id}.")
            send_callback(submission_id, 0.0)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Split text into chunks to respect token limitations
        chunks = chunk_text(text)
        logger.info(f"Running inference on {len(chunks)} text chunks...")
        
        weighted_ai = 0.0
        total_weight = 0
        
        if classifier:
            for chunk in chunks:
                predictions = classifier(chunk)
                parsed = parse_classifier_output(predictions[0] if isinstance(predictions[0], list) else predictions)
                weight = max(len(chunk.split()), 1)
                total_weight += weight
                weighted_ai += parsed.get("ai_score", 0.0) * weight
            
            final_ai_score = round(weighted_ai / total_weight, 2) if total_weight > 0 else 0.0
        else:
            logger.error("Classifier pipeline is uninitialized. Defaulting AI score to 0.0.")
            final_ai_score = 0.0

        # Send results back
        send_callback(submission_id, final_ai_score)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Successfully processed submission {submission_id} | Final AI Score: {final_ai_score}%")

    except Exception as e:
        logger.error(f"Error during message consumption: {str(e)}")
        try:
            # Re-queue on failure so message isn't lost
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        except Exception as nack_ex:
            logger.error(f"Failed to nack message: {str(nack_ex)}")

def main():
    while True:
        try:
            logger.info(f"Attempting connection to RabbitMQ host: '{RABBITMQ_HOST}'...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            
            # Queue declaration matching Java bean setup (durable=True)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            
            # Set prefetch limit
            channel.basic_qos(prefetch_count=1)
            
            # Register consumer callback
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_message)
            
            logger.info("AI Worker successfully connected and listening for messages...")
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"Connection to RabbitMQ lost: {str(e)}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"AI Worker loop encountered error: {str(e)}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    main()
