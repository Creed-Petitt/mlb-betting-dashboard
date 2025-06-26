import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
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
        SESSION_COOKIE_SAMESITE=app.config.get('SESSION_COOKIE_SAMESITE'),
        PERMANENT_SESSION_LIFETIME=app.config.get('PERMANENT_SESSION_LIFETIME')
    )
    
    # Initialize database
    db.init_app(app)
    
    # Initialize database migrations
    migrate = Migrate(app, db)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '200 per hour, 50 per minute')],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
        headers_enabled=app.config.get('RATELIMIT_HEADERS_ENABLED', True)
    )
    
    # Store limiter in app for use in routes
    app.limiter = limiter
    
    # CSRF exemptions for API endpoints (since they're stateless)
    csrf.exempt('main.get_props')
    csrf.exempt('main.get_teams')
    csrf.exempt('main.get_prop_matchup')
    csrf.exempt('main.get_players')
    csrf.exempt('main.get_games')
    csrf.exempt('main.get_stats_summary')
    csrf.exempt('main.health_check')
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database initialized successfully")
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")
            raise
    
    app.logger.info("MLB Bet AI application started successfully")
    return app

def setup_logging(app):
    """Configure application logging with rotation and proper formatting."""
    if not app.debug and not app.testing:
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Setup file handler with rotation
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'logs/app.log'),
            maxBytes=app.config.get('LOG_MAX_BYTES', 10485760),  # 10MB
            backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Set logging level
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
        app.logger.setLevel(log_level)
        
        app.logger.info('MLB Bet AI startup')