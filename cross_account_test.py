#!/usr/bin/env python3
"""
Cross-Account Email Testing System
Tests email flow from Hostinger to Gmail with interception, hold, modification, and release
"""

import smtplib
import imaplib
import sqlite3
import time
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import message_from_bytes, policy

# Account configurations
ACCOUNTS = {
    'hostinger': {
        'email': 'mcintyre@corrinbox.com',
        'password': 'Slaypap3!!',
        'smtp_host': 'smtp.hostinger.com',
        'smtp_port': 465,
        'imap_host': 'imap.hostinger.com',
        'imap_port': 993
    },
    'gmail': {
        'email': 'ndayijecika@gmail.com',
        'password': 'juzk lyge ugjo jalr',  # App Password with spaces
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'imap_host': 'imap.gmail.com',
        'imap_port': 993
    }
}

class CrossAccountEmailTest:
    """Manages cross-account email testing with interception"""
    
    def __init__(self):
        self.test_number = 1
        self.db_path = 'data/emails.db'
        
    def send_test_email(self, from_account='hostinger', to_account='gmail'):
        """Send test email from one account to another through proxy"""
        print("\n" + "="*70)
        print(f"📧 SENDING TEST EMAIL #{self.test_number}")
        print("="*70)
        
        from_config = ACCOUNTS[from_account]
        to_config = ACCOUNTS[to_account]
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = from_config['email']
        msg['To'] = to_config['email']
        msg['Subject'] = f"test {from_account} -> {to_account} #{self.test_number}"
        
        body = "original message"
        msg.attach(MIMEText(body, 'plain'))
        
        print(f"From: {from_config['email']}")
        print(f"To: {to_config['email']}")
        print(f"Subject: {msg['Subject']}")
        print(f"Body: {body}")
        
        # Send through SMTP proxy for interception
        try:
            print("\n🔄 Sending through SMTP proxy on localhost:8587...")
            proxy = smtplib.SMTP('localhost', 8587, timeout=10)
            proxy.send_message(msg)
            proxy.quit()
            print("✅ Email sent to proxy for interception")
            
            # Store test details
            test_info = {
                'test_number': self.test_number,
                'from': from_config['email'],
                'to': to_config['email'],
                'subject': msg['Subject'],
                'sent_at': datetime.now().isoformat()
            }
            
            self.test_number += 1
            return test_info
            
        except Exception as e:
            print(f"❌ Failed to send: {e}")
            return None    
    def check_interception(self, test_info):
        """Check if email was intercepted and stored in database"""
        print("\n🔍 Checking for intercepted email...")
        time.sleep(2)  # Wait for processing
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, sender, recipients, subject, body_text, status, created_at
                FROM email_messages
                WHERE subject = ?
                ORDER BY id DESC LIMIT 1
            ''', (test_info['subject'],))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print("✅ Email intercepted and stored!")
                # Parse recipients (stored as JSON list)
                recipients_str = result[2]
                if recipients_str.startswith('['):
                    import json
                    recipients = json.loads(recipients_str)
                    recipient = recipients[0] if recipients else result[2]
                else:
                    recipient = recipients_str
                
                email_data = {
                    'id': result[0],
                    'sender': result[1],
                    'recipient': recipient,
                    'subject': result[3],
                    'body': result[4],
                    'status': result[5],
                    'timestamp': result[6]
                }
                print(f"  ID: {email_data['id']}")
                print(f"  Status: {email_data['status']}")
                print(f"  Timestamp: {email_data['timestamp']}")
                return email_data
            else:
                print("❌ Email not found in database")
                return None
                
        except Exception as e:
            print(f"❌ Database error: {e}")
            return None    
    def hold_and_modify_email(self, email_data):
        """Hold email and modify it with timestamp"""
        print("\n⏸️ HOLDING EMAIL FOR MODIFICATION...")
        
        hold_start = datetime.now()
        print(f"Hold started at: {hold_start.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Simulate hold period
        hold_duration = 5  # seconds
        print(f"Holding for {hold_duration} seconds...")
        time.sleep(hold_duration)
        
        hold_end = datetime.now()
        duration = (hold_end - hold_start).total_seconds()
        
        # Create modified body with timestamp
        modified_body = f"""
=== EMAIL INTERCEPTED AND HELD ===
Hold Start: {hold_start.strftime('%Y-%m-%d %H:%M:%S')}
Hold Duration: {duration:.1f} seconds
Modified By: Cross-Account Test System
--- ORIGINAL MESSAGE BELOW ---
{email_data['body']}
--- MODIFICATION COMPLETE ---
Email was held and modified before release
"""
        
        # Update database with modified version
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE email_messages
                SET body_text = ?,
                    status = 'HELD',
                    review_notes = ?
                WHERE id = ?
            ''', (modified_body, f'Held for {duration:.1f} seconds', email_data['id']))
            
            conn.commit()
            conn.close()
            
            print("✅ Email modified with hold timestamp")
            print(f"Total hold duration: {duration:.1f} seconds")
            
            email_data['modified_body'] = modified_body
            email_data['hold_duration'] = duration
            return email_data
            
        except Exception as e:
            print(f"❌ Failed to modify email: {e}")
            return None
    
    def release_email(self, email_data):
        """Release modified email for delivery"""
        print("\n📤 RELEASING MODIFIED EMAIL...")
        
        try:
            # Update status to APPROVED for release
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE email_messages
                SET status = 'APPROVED',
                    reviewed_at = datetime('now')
                WHERE id = ?
            ''', (email_data['id'],))
            
            conn.commit()
            conn.close()
            
            print("✅ Email status changed to APPROVED")
            
            # Now send the modified email to Gmail
            gmail_config = ACCOUNTS['gmail']
            
            msg = MIMEMultipart()
            msg['From'] = email_data['sender']
            msg['To'] = email_data['recipient']
            msg['Subject'] = email_data['subject'] + " [MODIFIED]"
            
            # Use the modified body
            modified_body = email_data.get('modified_body', email_data['body'])
            msg.attach(MIMEText(modified_body, 'plain'))
            
            # Send directly to Gmail (not through proxy)
            print(f"Sending modified email to {gmail_config['email']}...")
            
            try:
                server = smtplib.SMTP(gmail_config['smtp_host'], gmail_config['smtp_port'])
                server.starttls()
                server.login(gmail_config['email'], gmail_config['password'])
                
                # Send as plain text
                text = msg.as_string()
                server.sendmail(email_data['sender'], email_data['recipient'], text)
                server.quit()
            except smtplib.SMTPAuthenticationError:
                # Try alternate send method
                print("Authentication failed, trying alternate method...")
                server = smtplib.SMTP_SSL(gmail_config['smtp_host'], 465)
                server.login(gmail_config['email'], gmail_config['password'])
                server.send_message(msg)
                server.quit()
            
            print("✅ Modified email sent to Gmail")
            return True
            
        except Exception as e:
            print(f"❌ Failed to release email: {e}")
            return False
    
    def verify_receipt(self, test_info):
        """Verify that only the modified email reached Gmail"""
        print("\n🔎 VERIFYING RECEIPT IN GMAIL...")
        time.sleep(5)  # Wait for delivery
        
        try:
            gmail_config = ACCOUNTS['gmail']
            
            # Connect to Gmail IMAP
            mail = imaplib.IMAP4_SSL(gmail_config['imap_host'], gmail_config['imap_port'])
            mail.login(gmail_config['email'], gmail_config['password'])
            mail.select('INBOX')
            
            # Search for emails with our test subject
            search_criteria = f'(SUBJECT "{test_info["subject"]}")'
            typ, msg_ids = mail.search(None, search_criteria)
            
            if not msg_ids[0]:
                print("❌ No emails found with test subject")
                return False
            
            email_ids = msg_ids[0].split()
            print(f"Found {len(email_ids)} email(s) with test subject")
            
            modified_found = False
            original_found = False
            
            for email_id in email_ids:
                typ, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                msg = message_from_bytes(raw_email, policy=policy.default)
                
                # Get email body
                body = msg.get_body(preferencelist=('plain', 'html'))
                if body:
                    body_text = body.get_content()
                    
                    # Check if this is the modified version
                    if "EMAIL INTERCEPTED AND HELD" in body_text:
                        modified_found = True
                        print("✅ Found MODIFIED email with timestamp")
                        
                        # Extract hold duration
                        for line in body_text.split('\n'):
                            if "Hold Duration:" in line:
                                print(f"  {line.strip()}")
                                break
                    
                    elif "original message" in body_text and "INTERCEPTED" not in body_text:
                        original_found = True
                        print("⚠️ Found ORIGINAL unmodified email")
            
            mail.close()
            mail.logout()
            
            # Analyze results
            if modified_found and not original_found:
                print("\n✅ SUCCESS: Only the modified email reached Gmail!")
                print("  ✓ Original was intercepted and blocked")
                print("  ✓ Modified version with timestamp was delivered")
                return True
            elif modified_found and original_found:
                print("\n⚠️ PARTIAL SUCCESS: Both emails found")
                print("  Modified email was delivered")
                print("  Original may have leaked through")
                return False
            else:
                print("\n❌ FAILURE: Modified email not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to verify receipt: {e}")
            return False
    
    def run_complete_test(self):
        """Run the complete cross-account test workflow"""
        print("\n" + "="*70)
        print("🚀 CROSS-ACCOUNT EMAIL TEST")
        print("="*70)
        print("Workflow: Send → Intercept → Hold → Modify → Release → Verify")
        print("From: mcintyre@corrinbox.com (Hostinger)")
        print("To: ndayijecika@gmail.com (Gmail)")
        print("="*70)
        
        # Step 1: Send test email
        test_info = self.send_test_email('hostinger', 'gmail')
        if not test_info:
            print("\n❌ Test failed at sending stage")
            return False
        
        # Step 2: Check interception
        email_data = self.check_interception(test_info)
        if not email_data:
            print("\n❌ Test failed at interception stage")
            return False
        
        # Step 3: Hold and modify
        modified_data = self.hold_and_modify_email(email_data)
        if not modified_data:
            print("\n❌ Test failed at modification stage")
            return False
        
        # Step 4: Release email
        if not self.release_email(modified_data):
            print("\n❌ Test failed at release stage")
            return False
        
        # Step 5: Verify receipt
        success = self.verify_receipt(test_info)
        
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        
        if success:
            print("✅ TEST PASSED!")
            print("  ✓ Email intercepted by proxy")
            print("  ✓ Email held and modified with timestamp")
            print(f"  ✓ Hold duration: {modified_data['hold_duration']:.1f} seconds")
            print("  ✓ Only modified email reached destination")
            print("  ✓ Original email was blocked")
        else:
            print("❌ TEST FAILED")
            print("  Check the steps above for details")
        
        print("="*70)
        return success


def main():
    """Main test execution"""
    tester = CrossAccountEmailTest()
    
    print("="*70)
    print("CROSS-ACCOUNT EMAIL TESTING SYSTEM")
    print("="*70)
    print("This will test email flow from Hostinger to Gmail")
    print("with interception, hold, modification, and release.")
    print("\nMAKE SURE:")
    print("1. The SMTP proxy is running (python simple_app.py)")
    print("2. Both email accounts are properly configured")
    print("3. The database is accessible")
    print("="*70)
    
    print("\nStarting test automatically...")
    
    # Run the complete test
    success = tester.run_complete_test()
    
    # Save test results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_passed': success,
            'test_number': tester.test_number - 1,
            'accounts': {
                'source': 'mcintyre@corrinbox.com',
                'destination': 'ndayijecika@gmail.com'
            }
        }, f, indent=2)
    
    print(f"\nTest results saved to: {results_file}")


if __name__ == "__main__":
    main()