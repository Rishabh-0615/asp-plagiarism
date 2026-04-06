"""Main Flask Application for AI Detection Service"""
import logging
import sys
from flask import Flask
from flask_cors import CORS
from config import config
from routes.detect_routes import detect_bp
from config import HF_MODEL_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get("ALLOWED_ORIGINS", []),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    app.register_blueprint(detect_bp)
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return {
            "service": "ASP Plagiarism - AI Detection Service",
            "version": "1.0.0",
            "status": "running",
            "model": HF_MODEL_ID,
            "code_mode": "code-hybrid-v1",
            "endpoints": {
                "health": "/api/v1/detect/health",
                "detect_text": "POST /api/v1/detect/text",
                "detect_file": "POST /api/v1/detect/file",
                "detect_cloudinary": "POST /api/v1/detect/cloudinary",
                "get_result": "GET /api/v1/detect/result/<submission_id>"
            }
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Endpoint not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return {"error": "Internal server error"}, 500
    
    logger.info("Flask application created successfully")
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info(f"Starting server on port {app.config['PORT']}")
    app.run(
        host='0.0.0.0',
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
