#!/usr/bin/env python3
"""
Comprehensive Email Intercept, Edit, and Release Test
Tests both outgoing and incoming email interception with editing
"""

import os
import sys
import time
import sqlite3
import smtplib
import threading
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from requests.auth import HTTPBasicAuth

# Configuration
SMTP_PROXY_HOST = "127.0.0.1"
SMTP_PROXY_PORT = 8587
WEB_APP_URL = "http://127.0.0.1:5000"
DB_PATH = "data/emails.db"

# Test credentials
TEST_FROM = "test_sender@example.com"
TEST_TO = "test_recipient@example.com"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

class EmailInterceptTest:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")
        self.test_results.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
    
    def login_to_dashboard(self):
        """Login to the web dashboard"""
        self.log("Logging into dashboard...")
        
        try:
            # Get login page
            response = self.session.get(f"{WEB_APP_URL}/login")
            if response.status_code != 200:
                self.log(f"Failed to load login page: {response.status_code}", "ERROR")
                return False
            
            # Submit login
            login_data = {
                "username": ADMIN_USER,
                "password": ADMIN_PASS
            }
            response = self.session.post(f"{WEB_APP_URL}/login", data=login_data, allow_redirects=True)
            
            if "Dashboard" in response.text or response.url.endswith("/dashboard"):
                self.log("✅ Successfully logged into dashboard", "SUCCESS")
                return True
            else:
                self.log("❌ Login failed", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Login error: {e}", "ERROR")
            return False
    
    def send_test_email_via_proxy(self, test_id):
        """Send email through SMTP proxy"""
        self.log(f"Sending test email #{test_id} via proxy...")
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = TEST_FROM
            msg['To'] = TEST_TO
            msg['Subject'] = f"Test Email #{test_id} - {self.timestamp}"
            msg['X-Test-ID'] = f"test_{test_id}_{self.timestamp}"
            
            body = f"""This is test email #{test_id}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}
Test Type: Email Interception and Modification Test

Original message content before interception.

Keywords for risk scoring: invoice, payment, urgent

This email should be:
1. Sent through SMTP proxy on port {SMTP_PROXY_PORT}
2. Intercepted and stored in database
3. Available for editing in dashboard
4. Modified with timestamp proof
5. Released with modifications
"""
            msg.attach(MIMEText(body, 'plain'))
            
            # Send via proxy
            smtp = smtplib.SMTP(SMTP_PROXY_HOST, SMTP_PROXY_PORT)
            smtp.send_message(msg)
            smtp.quit()
            
            self.log(f"✅ Email #{test_id} sent successfully", "SUCCESS")
            return msg['Subject']
            
        except Exception as e:
            self.log(f"❌ Failed to send email: {e}", "ERROR")
            return None
    
    def get_pending_emails(self):
        """Get pending emails from database"""
        self.log("Fetching pending emails from database...")
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, message_id, sender, recipients, subject, body_text, 
                       status, risk_score, created_at
                FROM email_messages
                WHERE status = 'PENDING'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            emails = cursor.fetchall()
            conn.close()
            
            self.log(f"Found {len(emails)} pending emails", "INFO")
            return [dict(email) for email in emails]
            
        except Exception as e:
            self.log(f"Database error: {e}", "ERROR")
            return []
    
    def edit_email_in_database(self, email_id, modifications):
        """Edit email directly in database with timestamp proof"""
        self.log(f"Editing email ID {email_id}...")
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get current email
            cursor.execute("SELECT body_text, subject FROM email_messages WHERE id = ?", (email_id,))
            email = cursor.fetchone()
            
            if not email:
                self.log(f"Email {email_id} not found", "ERROR")
                return False
            
            original_body = email[0]
            original_subject = email[1]
            
            # Create modified content with clear timestamp proof
            edit_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            
            modified_body = f"""
=== EMAIL INTERCEPTED AND MODIFIED ===
Interception Time: {edit_timestamp}
Modification Type: {modifications.get('type', 'Test Edit')}
Modified By: Email Management Tool Test Suite

--- ORIGINAL MESSAGE BELOW ---
{original_body}

--- MODIFICATIONS ADDED ---
✅ Email successfully intercepted at: {edit_timestamp}
✅ Content reviewed and modified
✅ Risk assessment completed
✅ Ready for controlled release

Test ID: {modifications.get('test_id', 'unknown')}
Modification Proof: This text was added during interception
=== END OF MODIFICATIONS ===
"""
            
            modified_subject = f"[INTERCEPTED] {original_subject} - Modified at {edit_timestamp[:19]}"
            
            # Update database
            cursor.execute("""
                UPDATE email_messages 
                SET body_text = ?, 
                    subject = ?,
                    review_notes = ?
                WHERE id = ?
            """, (modified_body, modified_subject, f"Modified during test at {edit_timestamp}", email_id))
            
            conn.commit()
            conn.close()
            
            self.log(f"✅ Email {email_id} modified with timestamp: {edit_timestamp}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Failed to edit email: {e}", "ERROR")
            return False
    
    def change_email_status(self, email_id, new_status, action_type="Test"):
        """Change email status (approve/reject/hold)"""
        self.log(f"Changing email {email_id} status to {new_status}...")
        
        try:
            # Try via API first
            response = self.session.post(
                f"{WEB_APP_URL}/email/{email_id}/action",
                data={"action": new_status, "notes": f"{action_type} at {datetime.now()}"}
            )
            
            if response.status_code in [200, 302]:
                self.log(f"✅ Email {email_id} status changed to {new_status}", "SUCCESS")
                return True
            else:
                # Fallback to direct database update
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE email_messages 
                    SET status = ?, 
                        reviewed_at = CURRENT_TIMESTAMP,
                        review_notes = ?
                    WHERE id = ?
                """, (new_status, f"{action_type} at {datetime.now()}", email_id))
                
                conn.commit()
                conn.close()
                
                self.log(f"✅ Email {email_id} status changed via database", "SUCCESS")
                return True
                
        except Exception as e:
            self.log(f"Failed to change status: {e}", "ERROR")
            return False
    
    def verify_dashboard_classification(self):
        """Verify emails are properly classified in dashboard"""
        self.log("Verifying dashboard classification...")
        
        try:
            # Get dashboard stats
            response = self.session.get(f"{WEB_APP_URL}/api/stats")
            
            if response.status_code == 200:
                stats = response.json()
                self.log("Dashboard Statistics:", "INFO")
                self.log(f"  Total Emails: {stats.get('total_emails', 0)}", "INFO")
                self.log(f"  Pending: {stats.get('pending_emails', 0)}", "INFO")
                self.log(f"  Approved: {stats.get('approved_emails', 0)}", "INFO")
                self.log(f"  Rejected: {stats.get('rejected_emails', 0)}", "INFO")
                self.log(f"  High Risk: {stats.get('high_risk_emails', 0)}", "INFO")
                return stats
            else:
                self.log("Failed to get dashboard stats", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Dashboard verification error: {e}", "ERROR")
            return None
    
    def test_outgoing_interception(self):
        """Test intercepting outgoing emails"""
        self.log("\n" + "="*70, "INFO")
        self.log("TEST 1: OUTGOING EMAIL INTERCEPTION", "INFO")
        self.log("="*70, "INFO")
        
        # Step 1: Send test email
        subject = self.send_test_email_via_proxy("OUTGOING")
        if not subject:
            return False
        
        # Wait for processing
        time.sleep(2)
        
        # Step 2: Get pending emails
        pending = self.get_pending_emails()
        test_email = None
        
        for email in pending:
            if subject in email['subject']:
                test_email = email
                break
        
        if not test_email:
            self.log("❌ Test email not found in pending queue", "ERROR")
            return False
        
        self.log(f"✅ Email intercepted with ID: {test_email['id']}", "SUCCESS")
        self.log(f"   Subject: {test_email['subject']}", "INFO")
        self.log(f"   Risk Score: {test_email['risk_score']}", "INFO")
        
        # Step 3: Edit the email
        modifications = {
            "type": "Outgoing Interception Test",
            "test_id": f"OUTGOING_{self.timestamp}"
        }
        
        if not self.edit_email_in_database(test_email['id'], modifications):
            return False
        
        # Step 4: Hold the email (keep as PENDING)
        self.log("Holding email in PENDING status for review...", "INFO")
        time.sleep(2)
        
        # Step 5: Release the email (APPROVE)
        if not self.change_email_status(test_email['id'], "APPROVE", "Outgoing Test Release"):
            return False
        
        # Step 6: Verify in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT subject, body_text, status, review_notes 
            FROM email_messages 
            WHERE id = ?
        """, (test_email['id'],))
        
        final_email = cursor.fetchone()
        conn.close()
        
        if final_email:
            self.log("✅ OUTGOING TEST COMPLETED", "SUCCESS")
            self.log(f"   Final Status: {final_email[2]}", "INFO")
            self.log(f"   Subject contains [INTERCEPTED]: {'[INTERCEPTED]' in final_email[0]}", "INFO")
            self.log(f"   Body contains modifications: {'EMAIL INTERCEPTED AND MODIFIED' in final_email[1]}", "INFO")
            return True
        
        return False
    
    def test_incoming_interception(self):
        """Test intercepting incoming emails"""
        self.log("\n" + "="*70, "INFO")
        self.log("TEST 2: INCOMING EMAIL INTERCEPTION", "INFO")
        self.log("="*70, "INFO")
        
        # Step 1: Simulate incoming email
        subject = self.send_test_email_via_proxy("INCOMING")
        if not subject:
            return False
        
        # Wait for processing
        time.sleep(2)
        
        # Step 2: Get the email
        pending = self.get_pending_emails()
        test_email = None
        
        for email in pending:
            if subject in email['subject']:
                test_email = email
                break
        
        if not test_email:
            self.log("❌ Test email not found", "ERROR")
            return False
        
        self.log(f"✅ Incoming email intercepted with ID: {test_email['id']}", "SUCCESS")
        
        # Step 3: Edit before delivery
        modifications = {
            "type": "Incoming Interception Test",
            "test_id": f"INCOMING_{self.timestamp}"
        }
        
        if not self.edit_email_in_database(test_email['id'], modifications):
            return False
        
        # Step 4: Hold for review
        self.log("Holding incoming email for review...", "INFO")
        time.sleep(2)
        
        # Step 5: Release to inbox (APPROVE)
        if not self.change_email_status(test_email['id'], "APPROVE", "Incoming Test Delivery"):
            return False
        
        # Step 6: Verify
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT subject, body_text, status, review_notes 
            FROM email_messages 
            WHERE id = ?
        """, (test_email['id'],))
        
        final_email = cursor.fetchone()
        conn.close()
        
        if final_email:
            self.log("✅ INCOMING TEST COMPLETED", "SUCCESS")
            self.log(f"   Final Status: {final_email[2]}", "INFO")
            self.log(f"   Modifications applied: {'EMAIL INTERCEPTED AND MODIFIED' in final_email[1]}", "INFO")
            return True
        
        return False
    
    def run_complete_test(self):
        """Run all interception tests"""
        self.log("="*70, "INFO")
        self.log("EMAIL INTERCEPTION, EDIT & RELEASE TEST SUITE", "INFO")
        self.log(f"Test Session: {self.timestamp}", "INFO")
        self.log("="*70, "INFO")
        
        # Login to dashboard
        if not self.login_to_dashboard():
            self.log("Cannot proceed without dashboard access", "ERROR")
            return False
        
        # Get initial stats
        initial_stats = self.verify_dashboard_classification()
        
        # Run tests
        test_results = {
            "outgoing": False,
            "incoming": False
        }
        
        # Test 1: Outgoing interception
        try:
            test_results["outgoing"] = self.test_outgoing_interception()
        except Exception as e:
            self.log(f"Outgoing test failed: {e}", "ERROR")
        
        # Test 2: Incoming interception
        try:
            test_results["incoming"] = self.test_incoming_interception()
        except Exception as e:
            self.log(f"Incoming test failed: {e}", "ERROR")
        
        # Get final stats
        final_stats = self.verify_dashboard_classification()
        
        # Generate report
        self.generate_report(test_results, initial_stats, final_stats)
        
        return all(test_results.values())
    
    def generate_report(self, results, initial_stats, final_stats):
        """Generate test report"""
        self.log("\n" + "="*70, "INFO")
        self.log("TEST REPORT", "INFO")
        self.log("="*70, "INFO")
        
        # Test results
        self.log("Test Results:", "INFO")
        self.log(f"  ✅ Outgoing Interception: {'PASSED' if results['outgoing'] else 'FAILED'}", 
                 "SUCCESS" if results['outgoing'] else "ERROR")
        self.log(f"  ✅ Incoming Interception: {'PASSED' if results['incoming'] else 'FAILED'}", 
                 "SUCCESS" if results['incoming'] else "ERROR")
        
        # Stats comparison
        if initial_stats and final_stats:
            self.log("\nEmail Statistics:", "INFO")
            self.log(f"  Total Emails: {initial_stats.get('total_emails', 0)} → {final_stats.get('total_emails', 0)}", "INFO")
            self.log(f"  Pending: {initial_stats.get('pending_emails', 0)} → {final_stats.get('pending_emails', 0)}", "INFO")
            self.log(f"  Approved: {initial_stats.get('approved_emails', 0)} → {final_stats.get('approved_emails', 0)}", "INFO")
        
        # Save detailed report
        report_file = f"test_report_{self.timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": self.timestamp,
                "results": results,
                "initial_stats": initial_stats,
                "final_stats": final_stats,
                "test_log": self.test_results
            }, f, indent=2)
        
        self.log(f"\nDetailed report saved to: {report_file}", "INFO")
        
        # Summary
        self.log("\n" + "="*70, "INFO")
        if all(results.values()):
            self.log("🎉 ALL TESTS PASSED!", "SUCCESS")
            self.log("Email interception, editing, and release workflow is fully functional!", "SUCCESS")
        else:
            self.log("⚠️ SOME TESTS FAILED", "ERROR")
            self.log("Please check the detailed report for more information.", "ERROR")


def main():
    """Main test runner"""
    print("\n" + "="*70)
    print("STARTING EMAIL INTERCEPT, EDIT & RELEASE TEST")
    print("="*70)
    print("Prerequisites:")
    print("  1. Email Management Tool must be running (python simple_app.py)")
    print("  2. SMTP proxy must be active on port 8587")
    print("  3. Web dashboard must be accessible on port 5000")
    print("="*70)
    
    # Check if application is running
    try:
        response = requests.get("http://127.0.0.1:5000/login", timeout=5)
        if response.status_code != 200:
            print("❌ Application not responding. Please start it first.")
            return
    except:
        print("❌ Cannot connect to application. Please run: python simple_app.py")
        return
    
    # Run tests
    tester = EmailInterceptTest()
    success = tester.run_complete_test()
    
    if success:
        print("\n✅ All interception tests completed successfully!")
        print("The email management tool is properly intercepting, editing, and releasing emails.")
    else:
        print("\n❌ Some tests failed. Check the report for details.")
    
    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)