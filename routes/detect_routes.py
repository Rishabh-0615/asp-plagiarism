"""API Routes for AI Detection"""
import logging
import base64
from flask import Blueprint, request, jsonify
from services.huggingface_service import HuggingFaceService
from services.cloudinary_service import CloudinaryService
from services.code_signal_service import CodeSignalService
from services.supabase_service import SupabaseService
from services.text_extraction import TextExtractionService
from config import CLOUDINARY_CLOUD_NAME, HF_MODEL_ID

logger = logging.getLogger(__name__)
detect_bp = Blueprint('detect', __name__, url_prefix='/api/v1/detect')

hf_service = HuggingFaceService()
cloudinary_service = CloudinaryService()
supabase_service = SupabaseService()
code_signal_service = CodeSignalService()


def _clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


def _combine_detection_scores(text: str, base_result: dict, file_name: str = "") -> dict:
    """Blend model score with code-aware signals when input is source code."""
    model_ai = float(base_result.get("ai_score", 0.0) or 0.0)
    model_conf = float(base_result.get("confidence", 0.0) or 0.0)

    if not TextExtractionService.is_code_file(file_name):
        enriched = dict(base_result)
        enriched["detection_mode"] = "text-model"
        return enriched

    heuristic = code_signal_service.score_code_ai_likelihood(text)
    heuristic_ai = float(heuristic.get("heuristic_ai_score", 0.0))
    heuristic_conf = float(heuristic.get("heuristic_confidence", 0.0))
    token_count = int(heuristic.get("signals", {}).get("token_count", 0))

    # Prefer code-aware signals for source files but keep model influence.
    if model_ai < 10.0:
        # The text model can severely under-score source code; trust heuristics more.
        combined_ai = (0.12 * model_ai) + (0.88 * heuristic_ai)
    elif token_count >= 120:
        combined_ai = (0.28 * model_ai) + (0.72 * heuristic_ai)
    elif token_count >= 60:
        combined_ai = (0.35 * model_ai) + (0.65 * heuristic_ai)
    else:
        combined_ai = (0.40 * model_ai) + (0.60 * heuristic_ai)

    # Calibration bump for known under-detection on generated code.
    combined_ai = _clamp_percent((combined_ai * 1.25) + 8.0)
    agreement = 1.0 - (abs(model_ai - heuristic_ai) / 100.0)
    combined_conf = max(0.0, min(1.0, (0.4 * model_conf) + (0.4 * heuristic_conf) + (0.2 * agreement)))

    label = "AI-generated" if combined_ai >= 48.0 else "Human-written"

    return {
        **base_result,
        "ai_score": round(combined_ai, 2),
        "human_score": round(100.0 - combined_ai, 2),
        "confidence": round(combined_conf, 2),
        "label": label,
        "detection_mode": "code-hybrid-v1",
        "model_ai_score": round(model_ai, 2),
        "heuristic_ai_score": round(heuristic_ai, 2),
        "signal_summary": heuristic.get("signals", {}),
    }


@detect_bp.route('/text', methods=['POST'])
def detect_ai_text():
    """
    Detect AI-generated content in plain text
    
    Request body:
    {
        "text": "submission text here",
        "submission_id": "sub_123",  # optional, to save to DB
        "save_to_db": true  # optional
    }
    
    Response:
    {
        "success": true,
        "ai_score": 85.5,
        "human_score": 14.5,
        "confidence": 0.95,
        "label": "AI-generated"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field"}), 400

        text = data.get('text', '').strip()
        submission_id = data.get('submission_id')
        file_name = data.get('file_name', '')
        is_code = bool(data.get('is_code', False))
        save_to_db = data.get('save_to_db', False)

        if not text:
            return jsonify({"error": "Empty text provided"}), 400

        # Run AI detection
        detection_result = hf_service.detect_ai_text(text)
        if is_code:
            inferred_name = file_name if file_name else "submission.java"
            detection_result = _combine_detection_scores(text, detection_result, inferred_name)
        elif file_name:
            detection_result = _combine_detection_scores(text, detection_result, file_name)

        # Save to Supabase if requested
        if save_to_db and submission_id:
            supabase_service.save_ai_detection(submission_id, detection_result)

        return jsonify({
            "success": True,
            "submission_id": submission_id,
            **detection_result
        }), 200

    except Exception as e:
        logger.error(f"Error in detect_ai_text: {str(e)}")
        return jsonify({"error": str(e)}), 500


@detect_bp.route('/file', methods=['POST'])
def detect_ai_file():
    """
    Detect AI-generated content from file URL
    
    Request body:
    {
        "file_url": "https://...",  # Cloudinary URL or public_id
        "submission_id": "sub_123",
        "save_to_db": true  # optional
    }
    
    Response:
    {
        "success": true,
        "ai_score": 85.5,
        "human_score": 14.5,
        "confidence": 0.95,
        "label": "AI-generated",
        "submission_id": "sub_123"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'file_url' not in data:
            return jsonify({"error": "Missing 'file_url' field"}), 400

        file_url = data.get('file_url')
        submission_id = data.get('submission_id')
        save_to_db = data.get('save_to_db', True)

        # Extract text from file
        text = TextExtractionService.extract_from_url(file_url)

        if not text:
            return jsonify({"error": "Could not extract text from file"}), 400

        # Run AI detection
        detection_result = hf_service.detect_ai_text(text)
        detection_result = _combine_detection_scores(text, detection_result, file_url)

        # Save to Supabase
        if save_to_db and submission_id:
            supabase_service.save_ai_detection(submission_id, detection_result)

        return jsonify({
            "success": True,
            "submission_id": submission_id,
            "file_url": file_url,
            **detection_result
        }), 200

    except Exception as e:
        logger.error(f"Error in detect_ai_file: {str(e)}")
        return jsonify({"error": str(e)}), 500


@detect_bp.route('/content', methods=['POST'])
def detect_ai_content():
    """
    Detect AI-generated content from base64-encoded file bytes.

    Request body:
    {
        "submission_id": "uuid",
        "file_name": "report.pdf",
        "file_content_base64": "...",
        "save_to_db": false
    }
    """
    try:
        data = request.get_json()

        if not data or 'file_content_base64' not in data:
            return jsonify({"error": "Missing 'file_content_base64' field"}), 400

        encoded = data.get('file_content_base64')
        file_name = data.get('file_name', 'submission.txt')
        submission_id = data.get('submission_id')
        save_to_db = data.get('save_to_db', False)

        try:
            file_bytes = base64.b64decode(encoded)
        except Exception:
            return jsonify({"error": "Invalid base64 content"}), 400

        text = TextExtractionService.extract_from_bytes(file_bytes, file_name)
        if not text:
            return jsonify({"error": "Could not extract text from content"}), 400

        detection_result = hf_service.detect_ai_text(text)
        detection_result = _combine_detection_scores(text, detection_result, file_name)

        if save_to_db and submission_id:
            supabase_service.save_ai_detection(submission_id, detection_result)

        return jsonify({
            "success": True,
            "submission_id": submission_id,
            "file_name": file_name,
            **detection_result
        }), 200

    except Exception as e:
        logger.error(f"Error in detect_ai_content: {str(e)}")
        return jsonify({"error": str(e)}), 500


@detect_bp.route('/cloudinary', methods=['POST'])
def detect_ai_cloudinary():
    """
    Detect AI-generated content from Cloudinary file
    
    Request body:
    {
        "public_id": "submissions/file123",  # Cloudinary public_id
        "submission_id": "sub_123",
        "save_to_db": true
    }
    
    Response:
    {
        "success": true,
        "ai_score": 85.5,
        "human_score": 14.5,
        "confidence": 0.95,
        "label": "AI-generated",
        "submission_id": "sub_123"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'public_id' not in data:
            return jsonify({"error": "Missing 'public_id' field"}), 400

        public_id = data.get('public_id')
        submission_id = data.get('submission_id')
        save_to_db = data.get('save_to_db', True)

        # Construct Cloudinary URL
        cloudinary_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/{public_id}"

        # Extract text from file
        text = TextExtractionService.extract_from_url(cloudinary_url)

        if not text:
            return jsonify({"error": "Could not extract text from Cloudinary file"}), 400

        # Run AI detection
        detection_result = hf_service.detect_ai_text(text)
        detection_result = _combine_detection_scores(text, detection_result, public_id)

        # Save to Supabase
        if save_to_db and submission_id:
            supabase_service.save_ai_detection(submission_id, detection_result)

        return jsonify({
            "success": True,
            "submission_id": submission_id,
            "public_id": public_id,
            **detection_result
        }), 200

    except Exception as e:
        logger.error(f"Error in detect_ai_cloudinary: {str(e)}")
        return jsonify({"error": str(e)}), 500


@detect_bp.route('/result/<submission_id>', methods=['GET'])
def get_detection_result(submission_id):
    """
    Retrieve saved AI detection result
    
    Response:
    {
        "success": true,
        "submission_id": "sub_123",
        "ai_score": 85.5,
        "human_score": 14.5,
        "confidence": 0.95,
        "label": "AI-generated",
        "detected_at": "2024-01-15T10:30:00"
    }
    """
    try:
        result = supabase_service.get_detection_by_submission(submission_id)

        if not result:
            return jsonify({"error": "Detection result not found"}), 404

        ai_percent = result.get("ai_generated_percent")
        label = "AI-generated" if (ai_percent or 0) >= 50 else "Human-written"

        return jsonify({
            "success": True,
            "submission_id": result.get("id"),
            "ai_score": ai_percent,
            "label": label,
            "content_type": result.get("content_type"),
            "file_url": result.get("file_url"),
            "file_name": result.get("file_name"),
            "submitted_at": result.get("submitted_at")
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving result: {str(e)}")
        return jsonify({"error": str(e)}), 500


@detect_bp.route('/health', methods=['GET'])
def health_check():
    """Service health check"""
    return jsonify({
        "status": "operational",
        "service": "asp-plagiarism (AI Detection)",
        "model": HF_MODEL_ID
    }), 200
