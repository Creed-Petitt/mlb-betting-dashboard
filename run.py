from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Use environment variables for debug, host, and port
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    
    print("\n" + "="*60)
    print("🚀 MLB BET AI DASHBOARD STARTING")
    print("="*60)
    print(f"📊 Dashboard URL: http://{host}:{port}")
    print(f"🔗 Click here: http://{host}:{port}")
    print("="*60)
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=debug, host=host, port=port)
