import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    DEBUG = False
    TESTING = False
    PORT = int(os.getenv('PORT', 5000))
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'

# API Credentials
HF_API_TOKEN = os.getenv('HF_API_TOKEN')
HF_MODEL_ID = os.getenv('HF_MODEL_ID', 'Hello-SimpleAI/chatgpt-detector-roberta')

CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_TABLE = os.getenv('SUPABASE_TABLE', 'submissions')

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8080')

# Get config based on environment
env = os.getenv('FLASK_ENV', 'development')
if env == 'production':
    config = ProductionConfig
else:
    config = DevelopmentConfig
