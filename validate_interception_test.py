#!/usr/bin/env python3
"""
Validation script for Email Interception and Editing Test Suite
Ensures all components are properly configured and functional
"""

import os
import sys
import sqlite3
import json
import requests
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
DB_PATH = "email_manager.db"

class TestValidator:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "passed": 0,
            "failed": 0
        }
    
    def check(self, name, test_func):
        """Run a check and log results"""
        try:
            result = test_func()
            if result:
                self.results["checks"].append({
                    "name": name,
                    "status": "passed",
                    "message": "Check passed"
                })
                self.results["passed"] += 1
                print(f"✅ {name}")
                return True
            else:
                self.results["checks"].append({
                    "name": name,
                    "status": "failed",
                    "message": "Check returned False"
                })
                self.results["failed"] += 1
                print(f"❌ {name}")
                return False
        except Exception as e:
            self.results["checks"].append({
                "name": name,
                "status": "failed",
                "error": str(e)
            })
            self.results["failed"] += 1
            print(f"❌ {name}: {e}")
            return False
    
    def check_files_exist(self):
        """Check if all required files exist"""
        required_files = [
            "simple_app.py",
            "email_interception_test.py",
            "playwright_interception_test.py",
            "templates/interception_test_dashboard.html",
            "templates/base.html",
            "email_manager.db"
        ]
        
        for file in required_files:
            if not os.path.exists(file):
                raise Exception(f"Missing file: {file}")
        
        return True
    
    def check_database_schema(self):
        """Check database has required tables and columns"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check email_accounts table
        cursor.execute("PRAGMA table_info(email_accounts)")
        account_columns = [col[1] for col in cursor.fetchall()]
        required_account_cols = ["id", "email_address", "is_active", "imap_host", "smtp_host"]
        
        for col in required_account_cols:
            if col not in account_columns:
                raise Exception(f"Missing column in email_accounts: {col}")
        
        # Check email_messages table
        cursor.execute("PRAGMA table_info(email_messages)")
        message_columns = [col[1] for col in cursor.fetchall()]
        required_message_cols = ["id", "subject", "body_text", "status", "sender", "recipients"]
        
        for col in required_message_cols:
            if col not in message_columns:
                raise Exception(f"Missing column in email_messages: {col}")
        
        conn.close()
        return True
    
    def check_active_accounts(self):
        """Check if there are at least 2 active email accounts"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        count = cursor.execute(
            "SELECT COUNT(*) FROM email_accounts WHERE is_active = 1"
        ).fetchone()[0]
        
        conn.close()
        
        if count < 2:
            raise Exception(f"Need at least 2 active accounts, found {count}")
        
        print(f"   Found {count} active email accounts")
        return True
    
    def check_app_running(self):
        """Check if the Flask app is running"""
        try:
            response = requests.get(BASE_URL, timeout=3)
            if response.status_code not in [200, 302]:  # 302 for login redirect
                raise Exception(f"App returned status {response.status_code}")
            return True
        except requests.ConnectionError:
            raise Exception("App is not running on port 5000")
    
    def check_test_dashboard_route(self):
        """Check if test dashboard route is accessible"""
        # Login first
        session = requests.Session()
        login_data = {"username": "admin", "password": "admin123"}
        
        login_response = session.post(f"{BASE_URL}/login", data=login_data)
        
        if login_response.status_code != 302:  # Should redirect after login
            raise Exception("Login failed")
        
        # Check test dashboard
        response = session.get(f"{BASE_URL}/interception-test")
        
        if response.status_code != 200:
            raise Exception(f"Test dashboard returned {response.status_code}")
        
        if "Email Interception" not in response.text:
            raise Exception("Test dashboard content not found")
        
        return True
    
    def check_api_endpoints(self):
        """Check if API endpoints are responding"""
        session = requests.Session()
        login_data = {"username": "admin", "password": "admin123"}
        session.post(f"{BASE_URL}/login", data=login_data)
        
        endpoints = [
            ("/api/accounts", "GET"),
            ("/api/test/check-interception?subject=test", "GET"),
        ]
        
        for endpoint, method in endpoints:
            url = f"{BASE_URL}{endpoint}"
            
            if method == "GET":
                response = session.get(url)
            else:
                response = session.post(url, json={})
            
            if response.status_code not in [200, 400]:  # 400 for expected validation errors
                raise Exception(f"{endpoint} returned {response.status_code}")
        
        return True
    
    def check_smtp_proxy(self):
        """Check if SMTP proxy is listening"""
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            result = sock.connect_ex(('localhost', 8587))
            sock.close()
            
            if result != 0:
                raise Exception("SMTP proxy not listening on port 8587")
            
            return True
        except Exception as e:
            raise Exception(f"SMTP proxy check failed: {e}")
    
    def check_playwright_installed(self):
        """Check if Playwright is installed"""
        try:
            import playwright
            from playwright.sync_api import sync_playwright
            
            # Check if browsers are installed
            with sync_playwright() as p:
                if not p.chromium.executable_path:
                    raise Exception("Chromium browser not installed")
            
            return True
        except ImportError:
            raise Exception("Playwright not installed. Run: pip install playwright && playwright install")
    
    def check_template_styling(self):
        """Check if template has proper styling"""
        template_path = "templates/interception_test_dashboard.html"
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for key styling elements
        required_elements = [
            "--primary-gradient",
            "flow-container",
            "timeline-item",
            "status-badge",
            "btn-primary"
        ]
        
        for element in required_elements:
            if element not in content:
                raise Exception(f"Missing styling element: {element}")
        
        return True
    
    def run_validation(self):
        """Run all validation checks"""
        print("\n" + "="*60)
        print("EMAIL INTERCEPTION TEST SUITE VALIDATION")
        print("="*60 + "\n")
        
        print("Running validation checks...\n")
        
        # Run checks
        self.check("Required files exist", self.check_files_exist)
        self.check("Database schema correct", self.check_database_schema)
        self.check("Active email accounts", self.check_active_accounts)
        self.check("Flask app running", self.check_app_running)
        self.check("Test dashboard route", self.check_test_dashboard_route)
        self.check("API endpoints responding", self.check_api_endpoints)
        self.check("SMTP proxy listening", self.check_smtp_proxy)
        self.check("Playwright installed", self.check_playwright_installed)
        self.check("Template styling complete", self.check_template_styling)
        
        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['failed'] == 0:
            print("\n🎉 ALL CHECKS PASSED! The test suite is ready to use.")
            print("\nTo run the test suite:")
            print("1. Ensure app is running: python simple_app.py")
            print("2. Run E2E test: python playwright_interception_test.py")
            print("3. Or visit: http://localhost:5000/interception-test")
        else:
            print("\n⚠️ Some checks failed. Please fix the issues above.")
        
        # Save results
        filename = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📊 Validation results saved to: {filename}")
        
        return self.results['failed'] == 0

def main():
    """Main validation runner"""
    validator = TestValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()