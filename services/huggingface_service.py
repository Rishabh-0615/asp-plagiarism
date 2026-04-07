"""Hugging Face Inference API Service for AI Detection"""
import requests
import logging
from requests.adapters import HTTPAdapter
from config import HF_API_TOKEN, HF_MODEL_ID

logger = logging.getLogger(__name__)

class HuggingFaceService:
    def __init__(self):
        self.api_token = HF_API_TOKEN
        self.model_id = HF_MODEL_ID
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{self.model_id}"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _chunk_text(self, text: str, max_words: int = 220, overlap: int = 30) -> list[str]:
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

    def _score_single_text(self, text: str) -> dict:
        """Score a single text chunk with the HF detector model."""
        payload = {"inputs": text}

        response = self.session.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=(5, 30)
        )

        if response.status_code != 200:
            logger.error(f"HuggingFace API error: {response.status_code} - {response.text}")
            return {
                "ai_score": 0.0,
                "human_score": 0.0,
                "confidence": 0.0,
                "error": f"API error: {response.status_code}"
            }

        result = response.json()

        ai_score = 0.0
        human_score = 0.0

        candidates = []
        if isinstance(result, list):
            if result and isinstance(result[0], list):
                candidates = result[0]
            else:
                candidates = result

        if candidates:
            for item in candidates:
                if isinstance(item, dict):
                    label = item.get('label', '').lower()
                    score = item.get('score', 0) * 100

                    if 'human' in label or 'written' in label:
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
            "ai_score": round(ai_score, 2),
            "human_score": round(human_score, 2),
            "confidence": round(confidence, 2),
            "label": label
        }

    def detect_ai_text(self, text: str) -> dict:
        """
        Detect AI-generated text using Desklib model
        
        Args:
            text (str): The submission text to analyze
            
        Returns:
            dict: AI detection result with confidence scores
                {
                    "ai_score": 85.5,  # AI likelihood percentage
                    "human_score": 14.5,  # Human likelihood percentage
                    "confidence": 0.95,
                    "label": "AI-generated"  # or "Human-written"
                }
        """
        try:
            if not text or len(text.strip()) == 0:
                return {
                    "ai_score": 0.0,
                    "human_score": 100.0,
                    "confidence": 0.0,
                    "label": "Empty text",
                    "error": "Empty submission text"
                }

            chunks = self._chunk_text(text)
            if len(chunks) == 1:
                detection_result = self._score_single_text(chunks[0])
            else:
                weighted_ai = 0.0
                weighted_human = 0.0
                total_weight = 0
                chunk_results = []

                for chunk in chunks:
                    chunk_result = self._score_single_text(chunk)
                    if chunk_result.get("error"):
                        logger.error(f"Chunk scoring error: {chunk_result.get('error')}")
                        continue

                    weight = max(len(chunk.split()), 1)
                    total_weight += weight
                    weighted_ai += chunk_result.get("ai_score", 0.0) * weight
                    weighted_human += chunk_result.get("human_score", 0.0) * weight
                    chunk_results.append(chunk_result)

                if total_weight == 0:
                    return {
                        "ai_score": 0.0,
                        "human_score": 0.0,
                        "confidence": 0.0,
                        "error": "No valid chunk scores returned"
                    }

                ai_score = weighted_ai / total_weight
                human_score = weighted_human / total_weight
                confidence = max(ai_score, human_score) / 100
                label = "AI-generated" if ai_score >= 50 else "Human-written"

                detection_result = {
                    "ai_score": round(ai_score, 2),
                    "human_score": round(human_score, 2),
                    "confidence": round(confidence, 2),
                    "label": label,
                    "chunks_analyzed": len(chunk_results)
                }

            logger.info(f"AI Detection Result: {detection_result}")
            return detection_result

        except requests.exceptions.Timeout:
            logger.error("HuggingFace API timeout")
            return {
                "ai_score": 0.0,
                "human_score": 0.0,
                "confidence": 0.0,
                "error": "API request timeout"
            }
        except Exception as e:
            logger.error(f"Error in AI detection: {str(e)}")
            return {
                "ai_score": 0.0,
                "human_score": 0.0,
                "confidence": 0.0,
                "error": str(e)
            }
