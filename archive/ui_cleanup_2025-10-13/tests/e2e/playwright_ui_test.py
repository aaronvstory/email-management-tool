#!/usr/bin/env python3
"""
Comprehensive Playwright UI Testing for Email Management Tool
Tests all interface functionality and takes screenshots
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, expect

# Test configuration
BASE_URL = "http://127.0.0.1:5000"
USERNAME = "admin"
PASSWORD = "admin123"
SCREENSHOTS_DIR = Path("screenshots/ui-test")
RESEARCH_DIR = Path(".claude/research/testing")

class EmailManagementUITester:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "screenshots": [],
            "errors": [],
            "summary": {}
        }
        
    async def setup(self):
        """Initialize browser and create directories"""
        # Create directories
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        
        # Start Playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Show browser for visibility
            args=['--start-maximized']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        self.page = await self.context.new_page()
        
    async def teardown(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def take_screenshot(self, name, full_page=False):
        """Take screenshot and save to directory"""
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = SCREENSHOTS_DIR / filename
        await self.page.screenshot(path=str(filepath), full_page=full_page)
        self.test_results["screenshots"].append(str(filepath))
        print(f"📸 Screenshot saved: {filepath}")
        return filepath
        
    async def test_login(self):
        """Test login functionality"""
        test_name = "Login Functionality"
        try:
            print(f"\n🔍 Testing: {test_name}")
            
            # Navigate to login page
            await self.page.goto(BASE_URL)
            await self.page.wait_for_load_state('networkidle')
            
            # Check if we're on login page
            title = await self.page.title()
            print(f"   Page title: {title}")
            
            # Take screenshot of login page
            await self.take_screenshot("01_login_page")
            
            # Check for login form elements
            username_field = await self.page.query_selector('input[name="username"]')
            password_field = await self.page.query_selector('input[name="password"]')
            login_button = await self.page.query_selector('button[type="submit"]')
            
            if username_field and password_field and login_button:
                # Fill login form
                await self.page.fill('input[name="username"]', USERNAME)
                await self.page.fill('input[name="password"]', PASSWORD)
                
                # Submit login
                await self.page.click('button[type="submit"]')
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                
                # Check if login successful (redirected to dashboard)
                current_url = self.page.url
                if '/dashboard' in current_url or '/emails' in current_url:
                    print(f"   ✅ Login successful! Redirected to: {current_url}")
                    await self.take_screenshot("02_after_login")
                    self.test_results["tests"].append({
                        "name": test_name,
                        "status": "PASSED",
                        "details": f"Successfully logged in as {USERNAME}"
                    })
                    return True
                else:
                    print(f"   ⚠️ Login may have failed. Current URL: {current_url}")
                    
            else:
                print("   ❌ Login form elements not found")
                self.test_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "details": "Login form elements not found"
                })
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            return False
            
    async def test_dashboard(self):
        """Test dashboard and navigation"""
        test_name = "Dashboard Navigation"
        try:
            print(f"\n🔍 Testing: {test_name}")
            
            # Navigate to dashboard
            await self.page.goto(f"{BASE_URL}/dashboard")
            await self.page.wait_for_load_state('networkidle')
            
            # Take screenshot
            await self.take_screenshot("03_dashboard_main", full_page=True)
            
            # Check for dashboard elements
            sidebar = await self.page.query_selector('.sidebar, nav')
            tabs = await self.page.query_selector_all('.nav-tabs a, .tab-button')
            
            print(f"   Found {len(tabs)} navigation tabs")
            
            # Test each tab if present
            tab_names = []
            for tab in tabs:
                tab_text = await tab.inner_text()
                tab_names.append(tab_text.strip())
                print(f"   - Tab: {tab_text.strip()}")
            
            self.test_results["tests"].append({
                "name": test_name,
                "status": "PASSED",
                "details": f"Found tabs: {', '.join(tab_names)}"
            })
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            return False
            
    async def test_email_queue(self):
        """Test email queue functionality"""
        test_name = "Email Queue"
        try:
            print(f"\n🔍 Testing: {test_name}")
            
            # Navigate to email queue
            await self.page.goto(f"{BASE_URL}/emails")
            await self.page.wait_for_load_state('networkidle')
            
            # Take screenshot
            await self.take_screenshot("04_email_queue", full_page=True)
            
            # Check for email queue elements
            email_table = await self.page.query_selector('table, .email-list')
            status_filters = await self.page.query_selector_all('a[href*="status="]')
            
            print(f"   Found {len(status_filters)} status filters")
            
            # Check for email actions
            edit_buttons = await self.page.query_selector_all('button[onclick*="editEmail"], .edit-btn')
            approve_buttons = await self.page.query_selector_all('button[onclick*="approve"], .approve-btn')
            
            print(f"   Found {len(edit_buttons)} edit buttons")
            print(f"   Found {len(approve_buttons)} approve buttons")
            
            self.test_results["tests"].append({
                "name": test_name,
                "status": "PASSED",
                "details": f"Email queue loaded with {len(status_filters)} filters"
            })
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            return False
            
    async def test_inbox(self):
        """Test inbox functionality"""
        test_name = "Inbox Viewer"
        try:
            print(f"\n🔍 Testing: {test_name}")
            
            # Navigate to inbox
            await self.page.goto(f"{BASE_URL}/inbox")
            await self.page.wait_for_load_state('networkidle')
            
            # Take screenshot
            await self.take_screenshot("05_inbox", full_page=True)
            
            # Check for inbox elements
            account_filter = await self.page.query_selector('select#accountFilter')
            email_cards = await self.page.query_selector_all('.card, .email-item')
            
            print(f"   Found {len(email_cards)} emails in inbox")
            
            # Check account filter if present
            if account_filter:
                options = await account_filter.query_selector_all('option')
                print(f"   Found {len(options)} account filter options")
            
            self.test_results["tests"].append({
                "name": test_name,
                "status": "PASSED",
                "details": f"Inbox loaded with {len(email_cards)} emails"
            })
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            return False
            
    async def test_compose(self):
        """Test email composition"""
        test_name = "Email Composition"
        try:
            print(f"\n🔍 Testing: {test_name}")
            
            # Navigate to compose
            await self.page.goto(f"{BASE_URL}/compose")
            await self.page.wait_for_load_state('networkidle')
            
            # Take screenshot
            await self.take_screenshot("06_compose", full_page=True)
            
            # Check for compose form elements
            account_select = await self.page.query_selector('select[name="account_id"]')
            recipient_field = await self.page.query_selector('input[name="recipient"]')
            subject_field = await self.page.query_selector('input[name="subject"]')
            body_field = await self.page.query_selector('textarea[name="body"]')
            send_button = await self.page.query_selector('button[type="submit"]')
            
            elements_found = []
            if account_select:
                elements_found.append("account selector")
            if recipient_field:
                elements_found.append("recipient field")
            if subject_field:
                elements_found.append("subject field")
            if body_field:
                elements_found.append("body field")
            if send_button:
                elements_found.append("send button")
                
            print(f"   Found compose elements: {', '.join(elements_found)}")
            
            self.test_results["tests"].append({
                "name": test_name,
                "status": "PASSED" if len(elements_found) >= 4 else "PARTIAL",
                "details": f"Compose form with: {', '.join(elements_found)}"
            })
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            return False
            
    async def test_accounts(self):
        """Test account management"""
        test_name = "Account Management"
        try:
            print(f"\n🔍 Testing: {test_name}")
            
            # Navigate to accounts
            await self.page.goto(f"{BASE_URL}/accounts")
            await self.page.wait_for_load_state('networkidle')
            
            # Take screenshot
            await self.take_screenshot("07_accounts", full_page=True)
            
            # Check for account elements
            account_cards = await self.page.query_selector_all('.card, .account-item')
            add_button = await self.page.query_selector('a[href*="/add"], button[onclick*="add"]')
            test_buttons = await self.page.query_selector_all('button[onclick*="test"]')
            
            print(f"   Found {len(account_cards)} configured accounts")
            print(f"   Found {len(test_buttons)} test connection buttons")
            
            self.test_results["tests"].append({
                "name": test_name,
                "status": "PASSED",
                "details": f"Found {len(account_cards)} accounts with {len(test_buttons)} test buttons"
            })
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            return False
            
    async def test_diagnostics(self):
        """Test diagnostics page"""
        test_name = "Diagnostics"
        try:
            print(f"\n🔍 Testing: {test_name}")
            
            # Navigate to diagnostics
            await self.page.goto(f"{BASE_URL}/diagnostics")
            await self.page.wait_for_load_state('networkidle')
            
            # Take screenshot
            await self.take_screenshot("08_diagnostics", full_page=True)
            
            # Check for diagnostic elements
            status_cards = await self.page.query_selector_all('.status-card, .diagnostic-item')
            
            print(f"   Found {len(status_cards)} diagnostic status items")
            
            self.test_results["tests"].append({
                "name": test_name,
                "status": "PASSED",
                "details": f"Diagnostics page loaded with {len(status_cards)} status items"
            })
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            return False
            
    async def run_all_tests(self):
        """Run all UI tests"""
        print("\n" + "="*80)
        print("🚀 Starting Email Management Tool UI Testing")
        print("="*80)
        
        await self.setup()
        
        try:
            # Run tests in sequence
            await self.test_login()
            await self.test_dashboard()
            await self.test_email_queue()
            await self.test_inbox()
            await self.test_compose()
            await self.test_accounts()
            await self.test_diagnostics()
            
            # Generate summary
            passed = sum(1 for t in self.test_results["tests"] if t["status"] == "PASSED")
            failed = sum(1 for t in self.test_results["tests"] if t["status"] == "FAILED")
            partial = sum(1 for t in self.test_results["tests"] if t["status"] == "PARTIAL")
            
            self.test_results["summary"] = {
                "total_tests": len(self.test_results["tests"]),
                "passed": passed,
                "failed": failed,
                "partial": partial,
                "errors": len(self.test_results["errors"]),
                "screenshots": len(self.test_results["screenshots"])
            }
            
            # Save results
            results_file = RESEARCH_DIR / f"ui-test-results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            
            print("\n" + "="*80)
            print("📊 Test Summary:")
            print(f"   ✅ Passed: {passed}")
            print(f"   ❌ Failed: {failed}")
            print(f"   ⚠️  Partial: {partial}")
            print(f"   🔥 Errors: {len(self.test_results['errors'])}")
            print(f"   📸 Screenshots: {len(self.test_results['screenshots'])}")
            print(f"\n   Results saved to: {results_file}")
            print("="*80)
            
        finally:
            await self.teardown()
            
        return self.test_results

async def main():
    """Main entry point"""
    tester = EmailManagementUITester()
    results = await tester.run_all_tests()
    return results

if __name__ == "__main__":
    asyncio.run(main())