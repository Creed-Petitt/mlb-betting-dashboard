import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from .models import db
from config import config

def create_app(config_name=None):
    """Application factory with enhanced configuration and logging."""
    app = Flask(__name__)
    
    # Load configuration properly
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Security configurations
    app.config.update(
        MAX_CONTENT_LENGTH=app.config.get('MAX_CONTENT_LENGTH'),
        SESSION_COOKIE_SECURE=app.config.get('SESSION_COOKIE_SECURE'),
        SESSION_COOKIE_HTTPONLY=app.config.get('SESSION_COOKIE_HTTPONLY'),
        SESSION_COOKIE_SAMESITE=app.config.get('SESSION_COOKIE_SAMESITE')
    )
    
    # Setup enhanced logging
    setup_logging(app)
    
    try:
        db.init_app(app)
        with app.app_context():
            db.create_all()
            app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")
        raise

    # Setup error handlers
    from .utils import setup_error_handlers
    setup_error_handlers(app)
    
    # Register routes
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    app.logger.info("MLB Bet AI application started successfully")
    return app

def setup_logging(app):
    """Configure enhanced logging with file rotation."""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Setup file handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # Set log level from environment
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    file_handler.setLevel(log_level)
    
    # Add handlers
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)
    
    # Console logging for development
    if app.debug or os.getenv('FLASK_ENV') == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        app.logger.addHandler(console_handler)
    
    # Disable default Flask logging to avoid duplicates
    logging.getLogger('werkzeug').setLevel(logging.WARNING)