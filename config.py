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
        'pool_size': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE', 5)),
        'pool_timeout': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_TIMEOUT', 20)),
        'pool_recycle': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE', 3600)),
        'max_overflow': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_MAX_OVERFLOW', 5)),
        'pool_pre_ping': True,  # Validates connections before use
        'connect_args': {
            'timeout': 30,
            'check_same_thread': False,
            'isolation_level': None  # Use autocommit mode to reduce lock contention
        }
    }
    
    # Security Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', 86400))  # 24 hours
    
    # Input Validation Limits
    MAX_INT_VALUE = int(os.environ.get('MAX_INT_VALUE', 2147483647))
    MAX_STRING_LENGTH = int(os.environ.get('MAX_STRING_LENGTH', 1000))
    
    # API Configuration
    FANDUEL_API_URL = os.environ.get('FANDUEL_API_URL') or 'https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page'
    FANDUEL_TIMEOUT = int(os.environ.get('FANDUEL_TIMEOUT', 15))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Pagination Defaults
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 50))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 1000))
    
    # Cache Settings
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', 60))
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')  # In-memory for development
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '200 per hour, 50 per minute')
    RATELIMIT_HEADERS_ENABLED = os.environ.get('RATELIMIT_HEADERS_ENABLED', 'True').lower() == 'true'

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'
    TESTING = False
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    
    # More lenient rate limits for development
    RATELIMIT_DEFAULT = '1000 per hour, 200 per minute'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    TESTING = False
    SESSION_COOKIE_SECURE = True  # HTTPS only in production
    
    # Stricter rate limits for production
    RATELIMIT_DEFAULT = '100 per hour, 20 per minute'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379')

class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 