"""Utility functions for the MLB Bet AI application."""

import os
import logging
import functools
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from flask import current_app, request, jsonify

def validate_integer_input(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None, field_name: str = "value") -> int:
    """Validate and sanitize integer input to prevent injection attacks."""
    try:
        # Convert to int, this will raise ValueError for invalid inputs
        int_value = int(value)
        
        # Check bounds
        if min_val is not None and int_value < min_val:
            raise ValueError(f"{field_name} must be at least {min_val}")
        
        max_allowed = max_val or current_app.config.get('MAX_INT_VALUE', 2147483647)
        if int_value > max_allowed:
            raise ValueError(f"{field_name} must be no more than {max_allowed}")
            
        return int_value
    except (ValueError, TypeError) as e:
        current_app.logger.warning(f"Invalid integer input for {field_name}: {value}")
        raise ValueError(f"Invalid {field_name}: must be a valid integer")

def validate_string_input(value: Any, max_length: Optional[int] = None, field_name: str = "value", allow_empty: bool = True) -> str:
    """Validate and sanitize string input to prevent injection attacks."""
    if value is None:
        if allow_empty:
            return ""
        raise ValueError(f"{field_name} cannot be empty")
    
    # Convert to string
    str_value = str(value)
    
    # Check for basic SQL injection patterns
    dangerous_patterns = [
        r"(?i)(union\s+select)",
        r"(?i)(drop\s+table)",
        r"(?i)(delete\s+from)",
        r"(?i)(insert\s+into)",
        r"(?i)(update\s+\w+\s+set)",
        r"(?i)(<script)",
        r"(?i)(javascript:)"
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, str_value):
            current_app.logger.warning(f"Potentially dangerous input detected in {field_name}: {str_value[:100]}")
            raise ValueError(f"Invalid {field_name}: contains prohibited content")
    
    # Check length
    max_allowed = max_length or current_app.config.get('MAX_STRING_LENGTH', 1000)
    if len(str_value) > max_allowed:
        raise ValueError(f"{field_name} must be no more than {max_allowed} characters")
    
    return str_value.strip()

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
                current_app.logger.warning(f"Input validation failed for {request.endpoint}: {str(e)}")
                return jsonify({"error": str(e)}), 400
        return wrapper
    return decorator

def log_api_call(func):
    """Decorator to log API calls and their performance."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        endpoint = request.endpoint or 'unknown'
        method = request.method
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            current_app.logger.info(
                f"API Call: {method} {endpoint} - Success - Duration: {duration:.3f}s - IP: {client_ip}"
            )
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            current_app.logger.error(
                f"API Call: {method} {endpoint} - Error: {str(e)} - Duration: {duration:.3f}s - IP: {client_ip}"
            )
            raise
    return wrapper

def handle_database_error(func):
    """Decorator to handle database errors gracefully."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Database error in {func.__name__}: {str(e)}")
            # Close the session to prevent issues
            from .models import db
            try:
                db.session.rollback()
            except:
                pass
            return jsonify({"error": "Database error occurred"}), 500
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
    """Perform application health check."""
    try:
        from .models import db, Prop, Player, Team
        
        # Check database connectivity
        prop_count = Prop.query.count()
        player_count = Player.query.count()
        team_count = Team.query.count()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connected": True,
                "props": prop_count,
                "players": player_count,
                "teams": team_count
            },
            "version": "1.0.0"
        }
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "database": {"connected": False}
        }

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