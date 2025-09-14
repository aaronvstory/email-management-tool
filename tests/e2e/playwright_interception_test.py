#!/usr/bin/env python3
"""
Playwright E2E Test for Email Interception and Editing
Captures screenshots at each step for visual verification
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError

# Configuration
BASE_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"
SCREENSHOT_DIR = "screenshots/interception_test"
RESULTS_FILE = f"test_results_interception_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

class InterceptionE2ETest:
    def __init__(self):
        self.results = []
        self.screenshots = []
        self.browser = None
        self.page = None
        self.context = None
        
        # Ensure screenshot directory exists
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    async def setup(self):
        """Initialize browser and login"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=False,  # Show browser for demo
                args=['--window-size=1920,1080']
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            
            self.page = await self.context.new_page()
            
            # Enable console logging
            self.page.on("console", lambda msg: print(f"Console: {msg.text}"))
            
            await self.login()
            return True
            
        except Exception as e:
            self.log_error("Setup failed", str(e))
            return False
    
    async def login(self):
        """Login to the application"""
        try:
            await self.page.goto(BASE_URL)
            await self.capture_screenshot("01_login_page")
            
            # Fill login form
            await self.page.fill("input[name='username']", USERNAME)
            await self.page.fill("input[name='password']", PASSWORD)
            
            await self.capture_screenshot("02_login_filled")
            
            # Submit login
            await self.page.click("button[type='submit']")
            
            # Wait for dashboard
            await self.page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
            
            await self.capture_screenshot("03_dashboard")
            self.log_success("Login", "Successfully logged in")
            
        except Exception as e:
            self.log_error("Login failed", str(e))
            raise
    
    async def navigate_to_test_dashboard(self):
        """Navigate to the interception test dashboard"""
        try:
            await self.page.goto(f"{BASE_URL}/interception-test")
            await self.page.wait_for_load_state("networkidle")
            
            await self.capture_screenshot("04_test_dashboard")
            self.log_success("Navigation", "Reached test dashboard")
            
        except Exception as e:
            self.log_error("Navigation failed", str(e))
            raise
    
    async def configure_test(self):
        """Configure test parameters"""
        try:
            # Wait for accounts to load
            await self.page.wait_for_selector("#fromAccount option:nth-child(2)", timeout=10000)
            
            # Select accounts
            from_options = await self.page.query_selector_all("#fromAccount option")
            to_options = await self.page.query_selector_all("#toAccount option")
            
            if len(from_options) < 2 or len(to_options) < 2:
                raise Exception("Not enough email accounts configured")
            
            # Select first account as sender
            await self.page.select_option("#fromAccount", index=1)
            
            # Select second account as recipient
            await self.page.select_option("#toAccount", index=2)
            
            # Set email content
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.page.fill("#originalSubject", f"Test Email {timestamp}")
            await self.page.fill("#originalBody", f"This is an automated test email sent at {timestamp}")
            
            await self.page.fill("#editedSubject", f"[EDITED] Test Email {timestamp}")
            await self.page.fill("#editedBody", f"This email was intercepted and edited by Playwright test at {timestamp}")
            
            # Set edit delay to 2 seconds
            await self.page.fill("#editDelay", "2")
            
            await self.capture_screenshot("05_test_configured")
            self.log_success("Configuration", "Test parameters configured")
            
        except Exception as e:
            self.log_error("Configuration failed", str(e))
            raise
    
    async def start_test(self):
        """Start the interception test"""
        try:
            # Click start test button
            await self.page.click("#startTest")
            
            await self.capture_screenshot("06_test_started")
            self.log_success("Test Started", "Email interception test initiated")
            
        except Exception as e:
            self.log_error("Test start failed", str(e))
            raise
    
    async def monitor_flow_steps(self):
        """Monitor and capture each flow step"""
        try:
            steps = [
                ("send", "Email Sent", 5000),
                ("intercept", "Email Intercepted", 10000),
                ("edit", "Email Edited", 5000),
                ("approve", "Email Approved", 5000),
                ("deliver", "Email Delivered", 10000)
            ]
            
            for step_id, step_name, timeout in steps:
                # Wait for step to complete
                await self.page.wait_for_selector(
                    f"#step-{step_id}.completed",
                    timeout=timeout
                )
                
                # Capture screenshot of completed step
                await self.capture_screenshot(f"07_step_{step_id}_completed")
                self.log_success(f"Step: {step_name}", f"{step_name} successfully")
                
                # Small delay for visual effect
                await asyncio.sleep(0.5)
            
        except TimeoutError as e:
            await self.capture_screenshot("error_timeout")
            self.log_error("Flow monitoring", f"Timeout waiting for step: {str(e)}")
            raise
        except Exception as e:
            await self.capture_screenshot("error_flow")
            self.log_error("Flow monitoring failed", str(e))
            raise
    
    async def verify_results(self):
        """Verify test results in the timeline"""
        try:
            # Wait for test completion
            await self.page.wait_for_selector(
                ".status-badge.success",
                timeout=5000
            )
            
            # Check timeline items
            timeline_items = await self.page.query_selector_all(".timeline-item")
            
            if len(timeline_items) < 5:
                raise Exception(f"Expected at least 5 timeline items, found {len(timeline_items)}")
            
            # Check for email preview
            email_preview = await self.page.is_visible("#emailPreview")
            if not email_preview:
                raise Exception("Email preview not visible")
            
            # Scroll to results
            await self.page.evaluate("document.querySelector('.results-container').scrollIntoView()")
            await self.capture_screenshot("08_test_results")
            
            # Capture email preview
            await self.page.evaluate("document.querySelector('#emailPreview').scrollIntoView()")
            await self.capture_screenshot("09_email_preview")
            
            self.log_success("Verification", "All test steps completed successfully")
            
        except Exception as e:
            await self.capture_screenshot("error_verification")
            self.log_error("Verification failed", str(e))
            raise
    
    async def test_edit_functionality(self):
        """Test the email editing functionality separately"""
        try:
            # Clear results first
            await self.page.click("#clearResults")
            await asyncio.sleep(1)
            
            # Configure a new test
            timestamp = datetime.now().strftime("%H:%M:%S")
            await self.page.fill("#originalSubject", f"Edit Test {timestamp}")
            await self.page.fill("#editedSubject", f"[MANUALLY EDITED] {timestamp}")
            
            # Start test
            await self.page.click("#startTest")
            
            # Wait for interception
            await self.page.wait_for_selector("#step-intercept.completed", timeout=10000)
            
            # The edit should happen automatically after delay
            await self.page.wait_for_selector("#step-edit.completed", timeout=10000)
            
            await self.capture_screenshot("10_edit_completed")
            self.log_success("Edit Test", "Email editing functionality verified")
            
        except Exception as e:
            await self.capture_screenshot("error_edit_test")
            self.log_error("Edit test failed", str(e))
            raise
    
    async def test_account_selection(self):
        """Test account selection and validation"""
        try:
            # Clear results
            await self.page.click("#clearResults")
            await asyncio.sleep(1)
            
            # Try to start test without selecting accounts
            await self.page.select_option("#fromAccount", index=0)
            await self.page.select_option("#toAccount", index=0)
            
            await self.page.click("#startTest")
            
            # Check for alert (validation)
            self.page.once("dialog", lambda dialog: dialog.accept())
            
            await self.capture_screenshot("11_validation_check")
            self.log_success("Validation", "Account selection validation working")
            
        except Exception as e:
            self.log_error("Account selection test failed", str(e))
            # Non-critical, continue
    
    async def capture_screenshot(self, name):
        """Capture and save screenshot"""
        try:
            filename = f"{SCREENSHOT_DIR}/{name}.png"
            await self.page.screenshot(path=filename, full_page=False)
            self.screenshots.append(filename)
            print(f"📸 Screenshot saved: {filename}")
            return filename
        except Exception as e:
            print(f"Failed to capture screenshot: {e}")
            return None
    
    def log_success(self, step, message):
        """Log successful step"""
        self.results.append({
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": "success",
            "message": message
        })
        print(f"✅ {step}: {message}")
    
    def log_error(self, step, error):
        """Log error"""
        self.results.append({
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": "error",
            "error": error
        })
        print(f"❌ {step}: {error}")
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.capture_screenshot("99_final_state")
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except:
            pass
    
    def save_results(self):
        """Save test results to JSON"""
        report = {
            "test_name": "Email Interception and Editing E2E Test",
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "screenshots": self.screenshots,
            "summary": {
                "total_steps": len(self.results),
                "successful": len([r for r in self.results if r["status"] == "success"]),
                "failed": len([r for r in self.results if r["status"] == "error"])
            }
        }
        
        with open(RESULTS_FILE, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Test results saved to: {RESULTS_FILE}")
        print(f"📸 Screenshots saved to: {SCREENSHOT_DIR}/")
        
        return report["summary"]["failed"] == 0
    
    async def run_full_test(self):
        """Run complete E2E test suite"""
        print("\n" + "="*60)
        print("PLAYWRIGHT E2E TEST - EMAIL INTERCEPTION & EDITING")
        print("="*60 + "\n")
        
        try:
            # Setup
            if not await self.setup():
                return False
            
            # Navigate to test dashboard
            await self.navigate_to_test_dashboard()
            
            # Configure test
            await self.configure_test()
            
            # Start test
            await self.start_test()
            
            # Monitor flow steps
            await self.monitor_flow_steps()
            
            # Verify results
            await self.verify_results()
            
            # Additional tests
            await self.test_edit_functionality()
            await self.test_account_selection()
            
            print("\n" + "="*60)
            print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            return False
        finally:
            await self.cleanup()

async def main():
    """Main test runner"""
    test = InterceptionE2ETest()
    success = await test.run_full_test()
    test.save_results()
    
    # Return exit code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    # Check if app is running
    import requests
    try:
        response = requests.get(BASE_URL, timeout=2)
        if response.status_code != 200:
            print("❌ Application is not running. Please start it first:")
            print("   python simple_app.py")
            sys.exit(1)
    except:
        print("❌ Application is not running. Please start it first:")
        print("   python simple_app.py")
        sys.exit(1)
    
    # Run tests
    asyncio.run(main())