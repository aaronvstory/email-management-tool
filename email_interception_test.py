#!/usr/bin/env python3
"""
Comprehensive Email Interception and Editing Test Suite
Tests the complete flow: Send -> Intercept -> Edit -> Deliver
"""

import os
import sys
import json
import time
import sqlite3
import smtplib
import imaplib
import email
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Database path
DB_PATH = 'email_manager.db'

class EmailInterceptionTest:
    def __init__(self):
        self.test_results = []
        self.accounts = []
        self.load_accounts()
    
    def load_accounts(self):
        """Load active email accounts from database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM email_accounts 
                WHERE is_active = 1
                ORDER BY account_name
            """)
            
            self.accounts = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            print(f"✅ Loaded {len(self.accounts)} active accounts")
            return True
        except Exception as e:
            print(f"❌ Failed to load accounts: {e}")
            return False
    
    def test_send_email(self, from_account, to_account, subject, body):
        """Send a test email through SMTP proxy"""
        try:
            # Send through our SMTP proxy on port 8587
            smtp = smtplib.SMTP('localhost', 8587)
            
            msg = MIMEMultipart()
            msg['From'] = from_account['email_address']
            msg['To'] = to_account['email_address']
            msg['Subject'] = subject
            msg['Date'] = email.utils.formatdate()
            msg['Message-ID'] = email.utils.make_msgid()
            
            msg.attach(MIMEText(body, 'plain'))
            
            smtp.send_message(msg)
            smtp.quit()
            
            self.test_results.append({
                'step': 'send_email',
                'status': 'success',
                'from': from_account['email_address'],
                'to': to_account['email_address'],
                'subject': subject,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✅ Email sent to proxy: {subject}")
            return True
            
        except Exception as e:
            self.test_results.append({
                'step': 'send_email',
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            print(f"❌ Failed to send email: {e}")
            return False
    
    def check_interception(self, subject):
        """Check if email was intercepted in database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Wait for email to appear in database
            for attempt in range(10):
                cursor.execute("""
                    SELECT * FROM email_messages 
                    WHERE subject = ? AND status = 'PENDING'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (subject,))
                
                email_row = cursor.fetchone()
                if email_row:
                    email_data = dict(email_row)
                    self.test_results.append({
                        'step': 'check_interception',
                        'status': 'success',
                        'email_id': email_data['id'],
                        'subject': email_data['subject'],
                        'timestamp': datetime.now().isoformat()
                    })
                    conn.close()
                    print(f"✅ Email intercepted with ID: {email_data['id']}")
                    return email_data['id']
                
                time.sleep(1)
            
            conn.close()
            self.test_results.append({
                'step': 'check_interception',
                'status': 'failed',
                'error': 'Email not found in database',
                'timestamp': datetime.now().isoformat()
            })
            print("❌ Email not intercepted")
            return None
            
        except Exception as e:
            self.test_results.append({
                'step': 'check_interception', 
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            print(f"❌ Failed to check interception: {e}")
            return None
    
    def edit_email(self, email_id, new_subject, new_body):
        """Edit the intercepted email"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Update email content
            cursor.execute("""
                UPDATE email_messages 
                SET subject = ?, 
                    body_text = ?,
                    review_notes = ?
                WHERE id = ?
            """, (new_subject, new_body, 
                  f"Edited by test suite at {datetime.now().isoformat()}", 
                  email_id))
            
            conn.commit()
            conn.close()
            
            self.test_results.append({
                'step': 'edit_email',
                'status': 'success',
                'email_id': email_id,
                'new_subject': new_subject,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✅ Email edited: {new_subject}")
            return True
            
        except Exception as e:
            self.test_results.append({
                'step': 'edit_email',
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            print(f"❌ Failed to edit email: {e}")
            return False
    
    def approve_email(self, email_id):
        """Approve the email for sending"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE email_messages 
                SET status = 'APPROVED',
                    approved_by = 'test_suite',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (email_id,))
            
            conn.commit()
            conn.close()
            
            self.test_results.append({
                'step': 'approve_email',
                'status': 'success',
                'email_id': email_id,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✅ Email approved for sending")
            return True
            
        except Exception as e:
            self.test_results.append({
                'step': 'approve_email',
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            print(f"❌ Failed to approve email: {e}")
            return False
    
    def verify_delivery(self, account, edited_subject):
        """Verify the edited email was delivered to destination"""
        try:
            # Wait for email to be sent
            time.sleep(5)
            
            # Connect to IMAP to check inbox
            if account['imap_use_ssl']:
                imap = imaplib.IMAP4_SSL(account['imap_host'], account['imap_port'])
            else:
                imap = imaplib.IMAP4(account['imap_host'], account['imap_port'])
            
            imap.login(account['imap_username'], account['imap_password'])
            imap.select('INBOX')
            
            # Search for email with edited subject
            _, messages = imap.search(None, f'(SUBJECT "{edited_subject}")')
            
            if messages[0]:
                self.test_results.append({
                    'step': 'verify_delivery',
                    'status': 'success',
                    'account': account['email_address'],
                    'subject': edited_subject,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"✅ Edited email delivered to {account['email_address']}")
                imap.close()
                imap.logout()
                return True
            
            imap.close()
            imap.logout()
            
            self.test_results.append({
                'step': 'verify_delivery',
                'status': 'failed',
                'error': 'Email not found in inbox',
                'timestamp': datetime.now().isoformat()
            })
            print("❌ Edited email not found in destination inbox")
            return False
            
        except Exception as e:
            self.test_results.append({
                'step': 'verify_delivery',
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            print(f"❌ Failed to verify delivery: {e}")
            return False
    
    def run_full_test(self, from_idx=0, to_idx=1):
        """Run complete interception and editing test"""
        if len(self.accounts) < 2:
            print("❌ Need at least 2 active accounts for cross-account testing")
            return False
        
        from_account = self.accounts[from_idx]
        to_account = self.accounts[to_idx]
        
        # Generate unique test data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_subject = f"Test Email {timestamp}"
        original_body = f"This is the original email body sent at {timestamp}"
        edited_subject = f"[EDITED] Test Email {timestamp}"
        edited_body = f"This email was edited by the test suite at {timestamp}"
        
        print("\n" + "="*60)
        print("EMAIL INTERCEPTION AND EDITING TEST")
        print("="*60)
        print(f"From: {from_account['email_address']}")
        print(f"To: {to_account['email_address']}")
        print(f"Original Subject: {original_subject}")
        print(f"Edited Subject: {edited_subject}")
        print("="*60 + "\n")
        
        # Step 1: Send email
        if not self.test_send_email(from_account, to_account, original_subject, original_body):
            return False
        
        # Step 2: Check interception
        email_id = self.check_interception(original_subject)
        if not email_id:
            return False
        
        # Step 3: Edit email
        if not self.edit_email(email_id, edited_subject, edited_body):
            return False
        
        # Step 4: Approve email
        if not self.approve_email(email_id):
            return False
        
        # Step 5: Verify delivery
        if not self.verify_delivery(to_account, edited_subject):
            return False
        
        print("\n" + "="*60)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*60 + "\n")
        
        return True
    
    def save_results(self):
        """Save test results to JSON file"""
        filename = f"interception_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump({
                'test_name': 'Email Interception and Editing Test',
                'timestamp': datetime.now().isoformat(),
                'accounts_tested': len(self.accounts),
                'results': self.test_results
            }, f, indent=2)
        print(f"📊 Test results saved to {filename}")
        return filename

def main():
    """Main test execution"""
    test = EmailInterceptionTest()
    
    if len(test.accounts) < 2:
        print("❌ Need at least 2 active email accounts to run test")
        sys.exit(1)
    
    # Run the full test
    success = test.run_full_test(0, 1)
    
    # Save results
    test.save_results()
    
    # Return status
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()