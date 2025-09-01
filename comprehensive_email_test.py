#!/usr/bin/env python3
"""
Comprehensive Email Management Tool Test
Tests the complete flow: send -> intercept -> edit -> receive
"""

import os
import sys
import time
import sqlite3
import smtplib
import imaplib
import ssl
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email
from email import policy
from email.parser import BytesParser

# Try importing with dotenv for credentials
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

class EmailFlowTester:
    def __init__(self):
        """Initialize with credentials from environment or hardcoded"""
        # Try environment variables first
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.hostinger.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '465'))
        self.imap_host = os.getenv('IMAP_HOST', 'imap.hostinger.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        
        # Credentials - CONFIRMED WORKING
        self.username = os.getenv('SMTP_USERNAME', 'mcintyre@corrinbox.com')
        self.password = os.getenv('SMTP_PASSWORD', 'Slaypap3!!')
        
        # Database path
        self.db_path = 'data/emails.db'
        
        print("=" * 70)
        print("COMPREHENSIVE EMAIL FLOW TEST")
        print("=" * 70)
        print(f"Configuration:")
        print(f"  SMTP: {self.smtp_host}:{self.smtp_port}")
        print(f"  IMAP: {self.imap_host}:{self.imap_port}")
        print(f"  Username: {self.username}")
        print(f"  Password: {'*' * (len(self.password)-2)}{self.password[-2:]}")
        print("=" * 70)
    
    def test_ssl_context_methods(self):
        """Test different SSL context configurations"""
        print("\n🔧 Testing SSL Context Methods...")
        
        contexts = [
            ("Default context", ssl.create_default_context()),
            ("No verification", self._create_unverified_context()),
            ("TLS 1.2", self._create_tls12_context()),
            ("Legacy", self._create_legacy_context()),
        ]
        
        for name, ctx in contexts:
            print(f"\n  Testing with {name}...")
            if self._test_imap_with_context(ctx):
                print(f"    ✅ {name} works for IMAP!")
                self.working_context = ctx
                return ctx
            else:
                print(f"    ❌ {name} failed")
        
        return None
    
    def _create_unverified_context(self):
        """Create SSL context without certificate verification"""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    
    def _create_tls12_context(self):
        """Create TLS 1.2 specific context"""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    
    def _create_legacy_context(self):
        """Create legacy SSL context"""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    
    def _test_imap_with_context(self, context):
        """Test IMAP connection with given SSL context"""
        try:
            imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=context)
            imap.login(self.username, self.password)
            imap.logout()
            return True
        except:
            return False
    
    def test_basic_connectivity(self):
        """Test basic SMTP and IMAP connectivity"""
        print("\n📡 Testing Basic Connectivity...")
        
        # Test IMAP
        print("  IMAP Connection:")
        try:
            # Try different auth methods
            for ssl_context in [None, self._create_unverified_context()]:
                try:
                    if ssl_context:
                        imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=ssl_context)
                    else:
                        imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                    
                    print(f"    Connected to {self.imap_host}")
                    
                    # Try login
                    imap.login(self.username, self.password)
                    print(f"    ✅ IMAP Authentication successful!")
                    
                    # Check folders
                    status, folders = imap.list()
                    print(f"    Found {len(folders)} folders")
                    
                    imap.logout()
                    break
                    
                except Exception as e:
                    if ssl_context is None:
                        print(f"    Trying with unverified SSL...")
                        continue
                    else:
                        print(f"    ❌ IMAP failed: {str(e)[:50]}")
                        
        except Exception as e:
            print(f"    ❌ IMAP connection failed: {e}")
        
        # Test SMTP
        print("\n  SMTP Connection:")
        try:
            # Try different auth methods
            for ssl_context in [None, self._create_unverified_context()]:
                try:
                    if ssl_context:
                        smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ssl_context)
                    else:
                        smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                    
                    print(f"    Connected to {self.smtp_host}")
                    
                    # Try login
                    smtp.login(self.username, self.password)
                    print(f"    ✅ SMTP Authentication successful!")
                    
                    smtp.quit()
                    break
                    
                except Exception as e:
                    if ssl_context is None:
                        print(f"    Trying with unverified SSL...")
                        continue
                    else:
                        print(f"    ❌ SMTP failed: {str(e)[:50]}")
                        
        except Exception as e:
            print(f"    ❌ SMTP connection failed: {e}")
    
    def send_test_email(self, subject_suffix=""):
        """Send a test email"""
        print(f"\n📤 Sending Test Email{subject_suffix}...")
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = self.username
            msg['Subject'] = f"Test Email {subject_suffix} - {datetime.now().strftime('%H:%M:%S')}"
            
            body = f"""This is a test email from the Email Management Tool.

Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Test type: {subject_suffix}

This email should be:
1. Sent via SMTP
2. Intercepted by the proxy
3. Stored in the database
4. Available for moderation

Keywords for testing: invoice, payment, urgent
"""
            msg.attach(MIMEText(body, 'plain'))
            
            # Send via SMTP
            ctx = self._create_unverified_context()
            smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ctx)
            smtp.login(self.username, self.password)
            smtp.send_message(msg)
            smtp.quit()
            
            print(f"    ✅ Email sent: {msg['Subject']}")
            return True
            
        except Exception as e:
            print(f"    ❌ Failed to send: {e}")
            return False
    
    def check_inbox(self):
        """Check inbox for test emails"""
        print("\n📥 Checking Inbox...")
        
        try:
            ctx = self._create_unverified_context()
            imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=ctx)
            imap.login(self.username, self.password)
            
            # Select inbox
            status, data = imap.select('INBOX')
            if status != 'OK':
                print("    ❌ Could not select INBOX")
                return []
            
            messages_count = int(data[0])
            print(f"    Total messages in INBOX: {messages_count}")
            
            # Search for recent test emails
            status, data = imap.search(None, 'SUBJECT "Test Email"')
            if status != 'OK':
                print("    No test emails found")
                return []
            
            email_ids = data[0].split()
            print(f"    Found {len(email_ids)} test emails")
            
            # Fetch last 5 test emails
            test_emails = []
            for email_id in email_ids[-5:]:
                status, data = imap.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    raw_email = data[0][1]
                    msg = BytesParser(policy=policy.default).parsebytes(raw_email)
                    test_emails.append({
                        'id': email_id.decode(),
                        'subject': msg['Subject'],
                        'from': msg['From'],
                        'date': msg['Date']
                    })
                    print(f"      - {msg['Subject']}")
            
            imap.logout()
            return test_emails
            
        except Exception as e:
            print(f"    ❌ Failed to check inbox: {e}")
            return []
    
    def check_database(self):
        """Check database for intercepted emails"""
        print("\n💾 Checking Database...")
        
        if not os.path.exists(self.db_path):
            print("    ❌ Database not found")
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for recent emails
            cursor.execute("""
                SELECT id, sender, subject, status, created_at, risk_score
                FROM email_messages
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            emails = cursor.fetchall()
            print(f"    Found {len(emails)} recent emails in database")
            
            for email in emails[:5]:
                print(f"      - [{email[3]}] {email[2]} (Risk: {email[5]})")
            
            conn.close()
            return emails
            
        except Exception as e:
            print(f"    ❌ Database error: {e}")
            return []
    
    def test_complete_flow(self):
        """Test the complete email flow"""
        print("\n" + "=" * 70)
        print("TESTING COMPLETE EMAIL FLOW")
        print("=" * 70)
        
        # 1. Test basic connectivity
        self.test_basic_connectivity()
        
        # 2. Send test email
        if self.send_test_email("Flow Test"):
            time.sleep(2)
            
            # 3. Check if received in inbox
            inbox_emails = self.check_inbox()
            
            # 4. Check if intercepted in database
            db_emails = self.check_database()
        
        # 5. Test interception flow
        print("\n🔄 Testing Interception Flow...")
        print("  1. Send email with trigger keywords")
        if self.send_test_email("URGENT INVOICE"):
            time.sleep(2)
            
            print("  2. Check if intercepted and held")
            db_emails = self.check_database()
            
            if db_emails:
                pending = [e for e in db_emails if e[3] == 'PENDING']
                print(f"     Found {len(pending)} pending emails for moderation")
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        
        print("\nSummary:")
        print("  • SMTP Connection: Check logs above")
        print("  • IMAP Connection: Check logs above")
        print("  • Email Sending: Check logs above")
        print("  • Email Reception: Check logs above")
        print("  • Database Storage: Check logs above")
        
        print("\nNext Steps:")
        print("  1. Start the application: python simple_app.py")
        print("  2. Navigate to: http://localhost:5000")
        print("  3. Login with: admin / admin123")
        print("  4. Check Email Queue for intercepted emails")
        print("  5. Approve/Reject emails for delivery")

def main():
    """Run the comprehensive test"""
    tester = EmailFlowTester()
    
    # First try to find working SSL context
    working_context = tester.test_ssl_context_methods()
    
    if working_context:
        print("\n✅ Found working SSL configuration!")
    
    # Run complete flow test
    tester.test_complete_flow()

if __name__ == "__main__":
    main()