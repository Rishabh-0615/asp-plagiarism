"""Flask Application for AI Detection Service - Health Check Only"""
import logging
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application for health checks"""
    app = Flask(__name__)
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            "status": "operational",
            "service": "asp-plagiarism (AI Detection Health Check)"
        }), 200
        
    @app.route('/api/v1/detect/health', methods=['GET'])
    def legacy_health():
        """Legacy health check endpoint for compatibility"""
        return jsonify({
            "status": "operational",
            "service": "asp-plagiarism (AI Detection Health Check)"
        }), 200

    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint returning basic service info"""
        return jsonify({
            "service": "asp-plagiarism (AI Detection)",
            "status": "operational",
            "info": "This HTTP server is for health checks only. AI detection tasks are processed asynchronously via RabbitMQ."
        }), 200

    logger.info("Flask health-check application created successfully")
    return app

app = create_app()

if __name__ == '__main__':
    # Flask development server guard
    logger.info("Starting Flask development server...")
    app.run(host='0.0.0.0', port=5000, debug=False)
