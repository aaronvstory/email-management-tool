#!/usr/bin/env python3
"""
Start the Email Management Tool and run UI tests
"""

import subprocess
import time
import requests
import sys
import os

def is_app_running():
    """Check if the Flask app is running"""
    try:
        response = requests.get("http://127.0.0.1:5000", timeout=2)
        return response.status_code in [200, 302]  # 302 for redirect to login
    except:
        return False

def start_app():
    """Start the Flask application"""
    print("🚀 Starting Email Management Tool...")
    # Start in background
    process = subprocess.Popen(
        [sys.executable, "simple_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # Wait for app to start
    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        if is_app_running():
            print("✅ Application started successfully!")
            return process
        if i % 5 == 0:
            print(f"   Waiting for app to start... ({i}s)")
    
    print("❌ Failed to start application")
    process.terminate()
    return None

def main():
    """Main execution"""
    app_process = None
    
    try:
        # Check if app is already running
        if is_app_running():
            print("✅ Application is already running")
        else:
            # Start the app
            app_process = start_app()
            if not app_process:
                sys.exit(1)
        
        # Run the Playwright tests
        print("\n🧪 Running UI tests...")
        result = subprocess.run(
            [sys.executable, "playwright_ui_test.py"],
            capture_output=False,
            text=True
        )
        
        return result.returncode
        
    finally:
        # Clean up
        if app_process:
            print("\n🛑 Stopping application...")
            app_process.terminate()
            time.sleep(2)
            if app_process.poll() is None:
                app_process.kill()

if __name__ == "__main__":
    sys.exit(main())