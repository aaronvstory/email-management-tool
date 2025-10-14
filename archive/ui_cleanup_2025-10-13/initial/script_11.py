# Create the main application runner and email delivery system
main_app_content = '''"""
Main Application Runner for Email Moderation System
Combines SMTP proxy and web interface
"""
import threading
import time
import logging
import configparser
import os
import sys
from app.smtp_proxy import SMTPProxyServer
from app.web_app import app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/email_moderation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_smtp_server():
    """Run SMTP proxy server in separate thread"""
    try:
        logger.info("Starting SMTP Proxy Server...")
        smtp_server = SMTPProxyServer()
        smtp_server.start()
    except Exception as e:
        logger.error(f"SMTP Server error: {e}")

def run_web_server():
    """Run Flask web server"""
    try:
        logger.info("Starting Web Interface...")
        # Load config
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        
        host = config.get('WEB_INTERFACE', 'host', fallback='127.0.0.1')
        port = config.getint('WEB_INTERFACE', 'port', fallback=5000)
        debug = config.getboolean('WEB_INTERFACE', 'debug', fallback=True)
        
        app.run(host=host, port=port, debug=debug, use_reloader=False)
    except Exception as e:
        logger.error(f"Web Server error: {e}")

def main():
    """Main application entry point"""
    print("="*60)
    print("Email Moderation System")
    print("="*60)
    print()
    
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Load and validate configuration
    config = configparser.ConfigParser()
    if not os.path.exists('config/config.ini'):
        logger.error("Configuration file not found: config/config.ini")
        return
    
    config.read('config/config.ini')
    
    # Display startup information
    smtp_port = config.getint('SMTP_PROXY', 'port', fallback=8587)
    web_port = config.getint('WEB_INTERFACE', 'port', fallback=5000)
    
    print(f"🔧 Configuration loaded")
    print(f"📧 SMTP Proxy will start on port {smtp_port}")
    print(f"🌐 Web Interface will start on port {web_port}")
    print(f"📊 Dashboard: http://127.0.0.1:{web_port}")
    print()
    print("🚀 Starting services...")
    print()
    
    try:
        # Start SMTP server in background thread
        smtp_thread = threading.Thread(target=run_smtp_server, daemon=True)
        smtp_thread.start()
        
        # Small delay to let SMTP server initialize
        time.sleep(2)
        
        # Start web server (blocking)
        run_web_server()
        
    except KeyboardInterrupt:
        logger.info("Shutting down Email Moderation System...")
        print("\\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Application error: {e}")

if __name__ == "__main__":
    main()
'''

with open("email_moderation_system/main.py", "w") as f:
    f.write(main_app_content)

print("Created main.py application runner")
print("✓ Threaded SMTP and web server startup")
print("✓ Configuration validation")
print("✓ Graceful shutdown handling")
print("✓ Comprehensive logging")