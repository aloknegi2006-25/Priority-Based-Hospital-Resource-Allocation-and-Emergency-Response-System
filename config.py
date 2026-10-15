import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Base configuration loaded from environment variables with safe defaults."""
    # Ephemeral random secret key for development sessions when not specified in .env;
    # avoids committing or deploying static placeholder secret keys.
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Database Configuration (Defaults for local development)
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'emergency_resource_db')

class TestConfig(Config):
    """Configuration for unit and scaffold tests."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'test-secret-key-testing-only'
