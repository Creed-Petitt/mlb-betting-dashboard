"""Utility functions for the MLB Bet AI application."""

import os
import logging
import functools
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from flask import current_app, request, jsonify, g

# Enhanced structured logging
class StructuredLogger:
    """Structured logger that outputs JSON for better parsing and analysis."""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
    
    def _log_structured(self, level: int, message: str, **kwargs):
        """Log a structured message with additional context."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'message': message,
            'level': logging.getLevelName(level),
            **kwargs
        }
        
        # Add request context if available
        if request:
            log_data.update({
                'request_id': getattr(g, 'request_id', None),
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')[:100]  # Truncate long user agents
            })
        
        self.logger.log(level, json.dumps(log_data, default=str))
    
    def info(self, message: str, **kwargs):
        self._log_structured(logging.INFO, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_structured(logging.ERROR, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_structured(logging.WARNING, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log_structured(logging.DEBUG, message, **kwargs)

# Create structured logger instances
security_logger = StructuredLogger('security')
performance_logger = StructuredLogger('performance')
api_logger = StructuredLogger('api')

def validate_integer_input(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None, field_name: str = "value") -> int:
    """Validate and sanitize integer input to prevent injection attacks."""
    try:
        # Convert to int, this will raise ValueError for invalid inputs
        int_value = int(value)
        
        # Check bounds
        if min_val is not None and int_value < min_val:
            security_logger.warning(f"Integer validation failed: {field_name} below minimum", 
                                  field=field_name, value=int_value, min_val=min_val)
            raise ValueError(f"{field_name} must be at least {min_val}")
        
        max_allowed = max_val or current_app.config.get('MAX_INT_VALUE', 2147483647)
        if int_value > max_allowed:
            security_logger.warning(f"Integer validation failed: {field_name} above maximum", 
                                  field=field_name, value=int_value, max_val=max_allowed)
            raise ValueError(f"{field_name} must be at most {max_allowed}")
        
        return int_value
    except (ValueError, TypeError) as e:
        security_logger.error(f"Integer validation error for {field_name}", 
                            field=field_name, value=str(value), error=str(e))
        raise ValueError(f"Invalid {field_name}: must be a valid integer")

def validate_string_input(value: Any, max_length: Optional[int] = None, field_name: str = "value", allow_empty: bool = True) -> str:
    """Validate and sanitize string input to prevent injection attacks."""
    try:
        if value is None:
            if allow_empty:
                return ""
            raise ValueError(f"{field_name} cannot be empty")
        
        # Convert to string
        str_value = str(value).strip()
        
        # Check if empty when not allowed
        if not allow_empty and not str_value:
            raise ValueError(f"{field_name} cannot be empty")
        
        # Check length
        max_len = max_length or current_app.config.get('MAX_STRING_LENGTH', 1000)
        if len(str_value) > max_len:
            security_logger.warning(f"String validation failed: {field_name} too long", 
                                  field=field_name, length=len(str_value), max_length=max_len)
            raise ValueError(f"{field_name} must be at most {max_len} characters")
        
        # Basic SQL injection pattern detection
        dangerous_patterns = [
            r"(\\'|\\\"|\\'\\\")",  # Quote escaping
            r"(;|\s+(or|and)\s+)",  # SQL keywords
            r"(union\s+select|drop\s+table|delete\s+from)",  # SQL operations
            r"(<script|javascript:|on\w+\s*=)",  # XSS patterns
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, str_value, re.IGNORECASE):
                security_logger.error(f"Dangerous pattern detected in {field_name}", 
                                    field=field_name, pattern=pattern, value=str_value[:100])
                raise ValueError(f"Invalid {field_name}: contains potentially dangerous content")
        
        return str_value
    except (ValueError, TypeError) as e:
        security_logger.error(f"String validation error for {field_name}", 
                            field=field_name, value=str(value)[:100] if value else None, error=str(e))
        raise ValueError(f"Invalid {field_name}: {str(e)}")

def validate_request_args():
    """Decorator to validate common request arguments for security."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Validate common parameters and store in g for access
                from flask import g
                if 'team_id' in request.args:
                    team_id = validate_integer_input(request.args.get('team_id'), min_val=1, field_name="team_id")
                    g.validated_team_id = team_id
                
                if 'per_page' in request.args:
                    per_page = validate_integer_input(
                        request.args.get('per_page'), 
                        min_val=1, 
                        max_val=current_app.config.get('MAX_PAGE_SIZE', 1000),
                        field_name="per_page"
                    )
                    g.validated_per_page = per_page
                
                if 'page' in request.args:
                    page = validate_integer_input(request.args.get('page'), min_val=1, field_name="page")
                    g.validated_page = page
                
                return func(*args, **kwargs)
                
            except ValueError as e:
                security_logger.warning(f"Request validation failed in {func.__name__}", 
                                      error=str(e),
                                      request_args=dict(request.args))
                return jsonify({"error": str(e)}), 400
        
        return wrapper
    return decorator

def log_api_call(func):
    """Enhanced decorator to log API calls with performance metrics and security context."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log successful API call
            api_logger.info(f"API Call: {request.method} {func.__name__}", 
                          duration=round(duration, 3),
                          status="success",
                          args_count=len(args),
                          kwargs_count=len(kwargs))
            
            # Log performance warning if slow
            if duration > 1.0:  # More than 1 second
                performance_logger.warning(f"Slow API call detected", 
                                         endpoint=func.__name__,
                                         duration=round(duration, 3))
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log API error
            api_logger.error(f"API Call failed: {request.method} {func.__name__}", 
                           duration=round(duration, 3),
                           status="error",
                           error_type=type(e).__name__,
                           error_message=str(e))
            raise
    
    return wrapper

def handle_database_error(func):
    """Enhanced decorator to handle database errors with proper logging."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log database error with context
            from sqlalchemy.exc import SQLAlchemyError
            
            if isinstance(e, SQLAlchemyError):
                security_logger.error(f"Database error in {func.__name__}", 
                                    error_type=type(e).__name__,
                                    error_message=str(e),
                                    function=func.__name__)
                return jsonify({"error": "Database error occurred"}), 500
            else:
                # Re-raise non-database errors
                raise
    
    return wrapper

def validate_pagination_params(page: Optional[int] = None, per_page: Optional[int] = None) -> Dict[str, int]:
    """Validate and sanitize pagination parameters."""
    default_page_size = current_app.config.get('DEFAULT_PAGE_SIZE', 50)
    max_page_size = current_app.config.get('MAX_PAGE_SIZE', 1000)
    
    # Validate page
    if page is None or page < 1:
        page = 1
    
    # Validate per_page
    if per_page is None:
        per_page = default_page_size
    elif per_page < 1:
        per_page = default_page_size
    elif per_page > max_page_size:
        per_page = max_page_size
    
    return {"page": page, "per_page": per_page}

def format_error_response(message: str, status_code: int = 400, details: Optional[Dict] = None) -> tuple:
    """Format consistent error responses."""
    response = {
        "error": message,
        "status_code": status_code,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        response["details"] = details
    
    current_app.logger.warning(f"Error response: {message} (Status: {status_code})")
    return jsonify(response), status_code

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert a value to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def get_date_range(days_ahead: int = 2) -> tuple:
    """Get date range for filtering props."""
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)
    return today, end_date

def health_check() -> Dict[str, Any]:
    """Perform application health check with structured logging."""
    try:
        from .models import db, Prop, Player, Team
        
        start_time = datetime.utcnow()
        
        # Check database connectivity
        prop_count = Prop.query.count()
        player_count = Player.query.count()
        team_count = Team.query.count()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connected": True,
                "props": prop_count,
                "players": player_count,
                "teams": team_count,
                "query_time": round(duration, 3)
            },
            "version": "1.0.0"
        }
        
        performance_logger.info("Health check completed", **health_data)
        return health_data
        
    except Exception as e:
        error_data = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "database": {"connected": False}
        }
        
        security_logger.error("Health check failed", **error_data)
        return error_data

def create_logs_directory():
    """Ensure logs directory exists."""
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"Created logs directory: {logs_dir}")

def setup_error_handlers(app):
    """Setup global error handlers for the Flask app."""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        app.logger.warning(f"400 error: {request.url} - {str(error)}")
        return jsonify({"error": "Bad request"}), 400
    
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 error: {request.url}")
        return jsonify({"error": "Resource not found"}), 404
    
    @app.errorhandler(413)
    def payload_too_large_error(error):
        app.logger.warning(f"413 error: Payload too large - {request.url}")
        return jsonify({"error": "Payload too large"}), 413
    
    @app.errorhandler(429)
    def too_many_requests_error(error):
        app.logger.warning(f"429 error: Too many requests - {request.url}")
        return jsonify({"error": "Too many requests"}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 error: {str(error)} - {request.url}")
        # Rollback database session on error
        from .models import db
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the full exception with stack trace
        app.logger.exception(f"Unhandled exception: {str(e)} - {request.url}")
        # Rollback database session on error
        from .models import db
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({"error": "An unexpected error occurred"}), 500 

def rate_limit_handler(e):
    """Custom rate limit handler with structured logging."""
    security_logger.warning("Rate limit exceeded", 
                          limit=str(e.limit),
                          retry_after=e.retry_after)
    return jsonify({
        "error": "Rate limit exceeded",
        "message": f"Too many requests. Try again in {e.retry_after} seconds.",
        "retry_after": e.retry_after
    }), 429 