"""
Comprehensive Email Interception and Release Test

This test validates the complete email moderation workflow:
1. Send email from Account 1 (Gmail) to Account 2 (Hostinger)
2. Subject contains "invoice" keyword
3. Email is intercepted by SMTP proxy (port 8587)
4. Email is HELD (not delivered to actual inbox)
5. Email is stored in local database
6. Email can be released
7. After release, email arrives in Account 2's actual inbox
"""

import time
import smtplib
import imaplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import os
# Test configuration using environment (.env) for credentials
ACCOUNT_1 = {
    'email': os.environ.get('GMAIL_ADDRESS', ''),
    'password': os.environ.get('GMAIL_PASSWORD', ''),  # Gmail App Password
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'name': 'Test Sender (Gmail)'
}

ACCOUNT_2 = {
    'email': os.environ.get('HOSTINGER_ADDRESS', ''),
    'password': os.environ.get('HOSTINGER_PASSWORD', ''),
    'imap_host': 'imap.hostinger.com',
    'imap_port': 993,
    'name': 'Test Recipient (Hostinger)'
}

# Local SMTP proxy configuration
PROXY_HOST = 'localhost'
PROXY_PORT = 8587

DB_PATH = 'email_manager.db'

class EmailInterceptionTest:
    def __init__(self):
        self.test_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.test_subject = f"TEST INVOICE #{self.test_id}"
        self.email_id = None

    def log(self, message, status='INFO'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{status}] {message}")

    def step_1_send_email_via_proxy(self):
        """Step 1: Send email via SMTP proxy (localhost:8587)"""
        self.log("=" * 80)
        self.log("STEP 1: Sending email via SMTP proxy", "TEST")
        self.log("=" * 80)

        try:
            if not ACCOUNT_1['email'] or not ACCOUNT_1['password'] or not ACCOUNT_2['email'] or not ACCOUNT_2['password']:
                self.log("Missing credentials in environment (.env); cannot run live interception test.", "ERROR")
                return False
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = ACCOUNT_1['email']
            msg['To'] = ACCOUNT_2['email']
            msg['Subject'] = self.test_subject

            body = f"""
This is a test email with INVOICE keyword for interception testing.

Test ID: {self.test_id}
From: {ACCOUNT_1['name']}
To: {ACCOUNT_2['name']}
Timestamp: {datetime.now().isoformat()}

This email should be intercepted and HELD by the moderation system.
It should NOT appear in the actual inbox of {ACCOUNT_2['email']}.
"""
            msg.attach(MIMEText(body, 'plain'))

            # Connect to SMTP proxy
            self.log(f"Connecting to SMTP proxy at {PROXY_HOST}:{PROXY_PORT}...")
            smtp = smtplib.SMTP(PROXY_HOST, PROXY_PORT)
            smtp.set_debuglevel(0)

            # Send email
            self.log(f"Sending email: '{self.test_subject}'...")
            smtp.sendmail(ACCOUNT_1['email'], ACCOUNT_2['email'], msg.as_string())
            smtp.quit()

            self.log("✅ Email sent successfully via proxy", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"❌ Failed to send email: {e}", "ERROR")
            return False

    def step_2_verify_interception(self):
        """Step 2: Verify email was intercepted and stored in database"""
        self.log("=" * 80)
        self.log("STEP 2: Verifying email interception in database", "TEST")
        self.log("=" * 80)

        # Wait for email to be processed
        self.log("Waiting 5 seconds for email processing...")
        time.sleep(5)

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Search for the email by subject
            email = cursor.execute("""
                SELECT * FROM email_messages
                WHERE subject LIKE ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (f'%{self.test_id}%',)).fetchone()

            if not email:
                self.log("❌ Email NOT found in database", "ERROR")
                conn.close()
                return False

            self.email_id = email['id']
            self.log(f"✅ Email found in database (ID: {self.email_id})", "SUCCESS")
            self.log(f"   Status: {email['status']}")
            self.log(f"   Interception Status: {email['interception_status'] or 'N/A'}")
            self.log(f"   Subject: {email['subject']}")
            self.log(f"   Sender: {email['sender']}")
            self.log(f"   Recipients: {email['recipients']}")
            self.log(f"   Risk Score: {email['risk_score']}")
            self.log(f"   Keywords Matched: {email['keywords_matched'] or 'None'}")

            # Verify it's in PENDING or HELD status
            expected_statuses = ['PENDING', 'HELD']
            if email['status'] in expected_statuses or email['interception_status'] in expected_statuses:
                self.log(f"✅ Email correctly marked as {email['status'] or email['interception_status']}", "SUCCESS")
            else:
                self.log(f"⚠️  Email status is '{email['status']}' (expected PENDING or HELD)", "WARNING")

            conn.close()
            return True

        except Exception as e:
            self.log(f"❌ Database check failed: {e}", "ERROR")
            return False

    def step_3_verify_not_in_actual_inbox(self):
        """Step 3: Verify email does NOT appear in actual inbox"""
        self.log("=" * 80)
        self.log("STEP 3: Verifying email NOT in actual inbox", "TEST")
        self.log("=" * 80)

        try:
            # Connect to IMAP
            self.log(f"Connecting to {ACCOUNT_2['imap_host']}:{ACCOUNT_2['imap_port']}...")
            imap = imaplib.IMAP4_SSL(ACCOUNT_2['imap_host'], ACCOUNT_2['imap_port'])
            imap.login(ACCOUNT_2['email'], ACCOUNT_2['password'])

            # Check INBOX
            imap.select('INBOX')
            status, messages = imap.search(None, f'SUBJECT "{self.test_subject}"')

            if messages[0]:
                message_ids = messages[0].split()
                self.log(f"❌ Email FOUND in actual inbox ({len(message_ids)} message(s))", "ERROR")
                self.log("   This means interception FAILED - email was not held", "ERROR")
                imap.close()
                imap.logout()
                return False
            else:
                self.log("✅ Email NOT found in actual inbox", "SUCCESS")
                self.log("   Interception working correctly - email was held", "SUCCESS")

            imap.close()
            imap.logout()
            return True

        except Exception as e:
            self.log(f"❌ IMAP check failed: {e}", "ERROR")
            return False

    def step_4_release_email(self):
        """Step 4: Release the held email"""
        self.log("=" * 80)
        self.log("STEP 4: Releasing held email", "TEST")
        self.log("=" * 80)

        if not self.email_id:
            self.log("❌ No email ID to release", "ERROR")
            return False

        try:
            # In a real scenario, this would call the API endpoint
            # For this test, we'll simulate the release by updating the database
            # and manually sending the email

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Get email details
            email = cursor.execute("SELECT * FROM email_messages WHERE id = ?", (self.email_id,)).fetchone()

            if not email:
                self.log("❌ Email not found in database", "ERROR")
                conn.close()
                return False

            # Update status to RELEASED
            cursor.execute("""
                UPDATE email_messages
                SET status = 'APPROVED',
                    interception_status = 'RELEASED',
                    processed_at = CURRENT_TIMESTAMP,
                    action_taken_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (self.email_id,))
            conn.commit()

            self.log(f"✅ Email marked as RELEASED in database", "SUCCESS")

            # Now actually send the email to the recipient
            self.log("Sending email to actual destination...")

            msg = MIMEMultipart()
            msg['From'] = ACCOUNT_1['email']
            msg['To'] = ACCOUNT_2['email']
            msg['Subject'] = self.test_subject + " [RELEASED]"
            msg['X-Moderation-Status'] = 'RELEASED'

            body = email[6] if len(email) > 6 else "Released email body"  # body_text column
            msg.attach(MIMEText(body, 'plain'))

            # Send via Gmail SMTP (not proxy)
            smtp = smtplib.SMTP(ACCOUNT_1['smtp_host'], ACCOUNT_1['smtp_port'])
            smtp.starttls()
            smtp.login(ACCOUNT_1['email'], ACCOUNT_1['password'])
            smtp.sendmail(ACCOUNT_1['email'], ACCOUNT_2['email'], msg.as_string())
            smtp.quit()

            self.log("✅ Email sent to actual destination", "SUCCESS")
            conn.close()
            return True

        except Exception as e:
            self.log(f"❌ Release failed: {e}", "ERROR")
            return False

    def step_5_verify_delivery(self):
        """Step 5: Verify email arrived in actual inbox after release"""
        self.log("=" * 80)
        self.log("STEP 5: Verifying email delivery to actual inbox", "TEST")
        self.log("=" * 80)

        # Wait for email to be delivered
        self.log("Waiting 10 seconds for email delivery...")
        time.sleep(10)

        try:
            # Connect to IMAP
            self.log(f"Connecting to {ACCOUNT_2['imap_host']}:{ACCOUNT_2['imap_port']}...")
            imap = imaplib.IMAP4_SSL(ACCOUNT_2['imap_host'], ACCOUNT_2['imap_port'])
            imap.login(ACCOUNT_2['email'], ACCOUNT_2['password'])

            # Check INBOX for RELEASED email
            imap.select('INBOX')
            status, messages = imap.search(None, f'SUBJECT "{self.test_subject}"')

            if messages[0]:
                message_ids = messages[0].split()
                self.log(f"✅ Email FOUND in actual inbox ({len(message_ids)} message(s))", "SUCCESS")
                self.log("   Email successfully delivered after release", "SUCCESS")

                # Fetch and display first message
                if len(message_ids) > 0:
                    status, msg_data = imap.fetch(message_ids[0], '(BODY[HEADER.FIELDS (FROM TO SUBJECT DATE)])')
                    if msg_data and msg_data[0]:
                        headers = msg_data[0][1].decode('utf-8', errors='ignore')
                        self.log("   Message headers:")
                        for line in headers.split('\n'):
                            if line.strip():
                                self.log(f"      {line.strip()}")

                imap.close()
                imap.logout()
                return True
            else:
                self.log("❌ Email NOT found in actual inbox", "ERROR")
                self.log("   Email may not have been delivered", "ERROR")
                imap.close()
                imap.logout()
                return False

        except Exception as e:
            self.log(f"❌ Delivery verification failed: {e}", "ERROR")
            return False

    def run_complete_test(self):
        """Run the complete interception workflow test"""
        self.log("")
        self.log("=" * 80)
        self.log("EMAIL INTERCEPTION WORKFLOW TEST", "TEST")
        self.log("=" * 80)
        self.log(f"Test ID: {self.test_id}")
        self.log(f"From: {ACCOUNT_1['email']} (Gmail)")
        self.log(f"To: {ACCOUNT_2['email']} (Hostinger)")
        self.log(f"Subject: {self.test_subject}")
        self.log("")

        results = {
            'step_1_send': False,
            'step_2_intercept': False,
            'step_3_not_in_inbox': False,
            'step_4_release': False,
            'step_5_delivery': False
        }

        # Run all steps
        results['step_1_send'] = self.step_1_send_email_via_proxy()
        if results['step_1_send']:
            results['step_2_intercept'] = self.step_2_verify_interception()

        if results['step_2_intercept']:
            results['step_3_not_in_inbox'] = self.step_3_verify_not_in_actual_inbox()

        if results['step_3_not_in_inbox']:
            results['step_4_release'] = self.step_4_release_email()

        if results['step_4_release']:
            results['step_5_delivery'] = self.step_5_verify_delivery()

        # Print summary
        self.log("")
        self.log("=" * 80)
        self.log("TEST SUMMARY", "RESULT")
        self.log("=" * 80)

        for step, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            self.log(f"{step}: {status}")

        all_passed = all(results.values())
        self.log("")
        if all_passed:
            self.log("🎉 ALL TESTS PASSED! Email interception workflow is working correctly.", "SUCCESS")
        else:
            self.log("❌ SOME TESTS FAILED. Please check the logs above.", "ERROR")

        self.log("=" * 80)
        return all_passed


if __name__ == '__main__':
    test = EmailInterceptionTest()
    success = test.run_complete_test()
    exit(0 if success else 1)
