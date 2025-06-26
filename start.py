#!/usr/bin/env python3
"""
Production startup script for MLB Bet AI
Handles environment setup, logging, and graceful startup/shutdown
"""

import os
import sys
import signal
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Setup environment variables and directories."""
    # Create necessary directories
    directories = ['logs', 'data', 'instance']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Directory ensured: {directory}")
    
    # Set default environment variables if not set
    env_defaults = {
        'FLASK_ENV': 'production',
        'LOG_LEVEL': 'INFO',
        'DATABASE_URL': 'sqlite:///C:/Users/highs/mlb-bet-ai/data/mlb.db'
    }
    
    for key, default_value in env_defaults.items():
        if not os.getenv(key):
            os.environ[key] = default_value
            print(f"✓ Set default {key}={default_value}")

def signal_handler(signum, frame):
    """Handle graceful shutdown."""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main startup function."""
    print("🚀 Starting MLB Bet AI Application")
    print("=" * 50)
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Setup environment
        setup_environment()
        
        # Import and create Flask app
        from app import create_app
        app = create_app()
        
        # Get configuration
        host = os.getenv('HOST', '127.0.0.1')
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_ENV') == 'development'
        
        print(f"✓ Application configured")
        print(f"✓ Environment: {os.getenv('FLASK_ENV', 'development')}")
        print(f"✓ Debug mode: {debug}")
        print(f"✓ Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("=" * 50)
        print(f"🌐 Starting server on http://{host}:{port}")
        print("💡 Press Ctrl+C to stop")
        print("=" * 50)
        
        # Start the application
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            threaded=True
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 