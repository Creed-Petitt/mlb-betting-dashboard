import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration - CRITICAL: Keep using data/mlb.db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.abspath("data/mlb.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database Connection Pooling for resilience
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE', 10)),
        'pool_timeout': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_TIMEOUT', 20)),
        'pool_recycle': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE', 3600)),
        'max_overflow': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_MAX_OVERFLOW', 20)),
        'pool_pre_ping': True  # Validates connections before use
    }
    
    # Security Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    
    # Input Validation Limits
    MAX_INT_VALUE = int(os.environ.get('MAX_INT_VALUE', 2147483647))
    MAX_STRING_LENGTH = int(os.environ.get('MAX_STRING_LENGTH', 1000))
    
    # API Configuration
    FANDUEL_API_URL = os.environ.get('FANDUEL_API_URL') or 'https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page'
    FANDUEL_TIMEOUT = int(os.environ.get('FANDUEL_TIMEOUT', 15))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # Pagination Defaults
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 50))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 1000))
    
    # Cache Settings
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', 60))

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    # Override with more secure defaults for production
    SESSION_COOKIE_SECURE = True
    # Keep using SQLite but with the same path
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.abspath("data/mlb.db")}'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 