#!/usr/bin/env python3
"""
Email Management Tool - Main Application Entry Point
Production-ready email moderation system with modern dashboard
"""

import os
import sys
import threading
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure required directories exist"""
    directories = ['logs', 'data', 'uploads', 'temp']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def run_smtp_proxy():
    """Run SMTP proxy server in background thread"""
    try:
        from app.services.smtp_proxy import SMTPProxyServer
        logger.info("Starting SMTP Proxy Server on port 8587...")
        proxy = SMTPProxyServer()
        proxy.start()
    except Exception as e:
        logger.error(f"Failed to start SMTP proxy: {e}")

def run_flask_app():
    """Run Flask web application"""
    try:
        from app import create_app
        
        # Create Flask app
        app = create_app('development')
        
        # Get configuration
        host = app.config.get('WEB_HOST', '127.0.0.1')
        port = app.config.get('WEB_PORT', 5000)
        debug = app.config.get('DEBUG', True)
        
        logger.info(f"Starting Flask app on {host}:{port}")
        
        # Run Flask app
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,  # Disable reloader to prevent double startup
            threaded=True
        )
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}")
        raise

def print_startup_banner():
    """Print application startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║           EMAIL MANAGEMENT TOOL - ENTERPRISE EDITION            ║
    ║                                                                  ║
    ║                  Modern Email Moderation System                 ║
    ║                        Version 2.0.0                            ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    print("    🚀 Starting services...")
    print(f"    📧 SMTP Proxy: Port 8587")
    print(f"    🌐 Web Dashboard: http://127.0.0.1:5000")
    print(f"    👤 Default Login: admin / admin123")
    print()
    print("    ⚡ Features:")
    print("    • Real-time email moderation")
    print("    • Advanced rule engine")
    print("    • Modern responsive dashboard")
    print("    • Complete audit trail")
    print("    • Multi-user support with roles")
    print()
    print("    Press Ctrl+C to stop the application")
    print("    " + "="*60)
    print()

def main():
    """Main application entry point"""
    try:
        # Print startup banner
        print_startup_banner()
        
        # Ensure required directories exist
        ensure_directories()
        
        # Start SMTP proxy in background thread
        smtp_thread = threading.Thread(target=run_smtp_proxy, daemon=True)
        smtp_thread.start()
        logger.info("SMTP proxy thread started")
        
        # Give SMTP proxy time to start
        time.sleep(2)
        
        # Run Flask app (blocking)
        run_flask_app()
        
    except KeyboardInterrupt:
        print("\n\n    👋 Shutting down Email Management Tool...")
        print("    Thank you for using our system!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n    ❌ Error: {e}")
        print("    Check logs/app.log for details")
        sys.exit(1)

if __name__ == "__main__":
    main()