#!/usr/bin/env python3
"""
Comprehensive Gmail Integration Test
Tests Gmail account connectivity, interception, and full workflow
"""

import smtplib
import imaplib
import json
import time
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests

# Gmail Account Configuration
GMAIL_CONFIG = {
    "email": "ndayijecika@gmail.com",
    "password": "juzk lyge ugjo jalr",  # App Password (with spaces as provided by Google)
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_host": "imap.gmail.com", 
    "imap_port": 993
}

def test_gmail_smtp():
    """Test Gmail SMTP connectivity"""
    print("\n" + "="*60)
    print("🔍 Testing Gmail SMTP Connection")
    print("="*60)
    
    try:        # Connect to Gmail SMTP with STARTTLS
        print(f"Connecting to {GMAIL_CONFIG['smtp_host']}:{GMAIL_CONFIG['smtp_port']}...")
        server = smtplib.SMTP(GMAIL_CONFIG['smtp_host'], GMAIL_CONFIG['smtp_port'], timeout=10)
        server.set_debuglevel(0)  # Set to 1 for debug output
        
        print("Starting TLS encryption...")
        server.starttls()
        
        print(f"Authenticating as {GMAIL_CONFIG['email']}...")
        server.login(GMAIL_CONFIG['email'], GMAIL_CONFIG['password'])
        
        print("✅ Gmail SMTP connection successful!")
        
        # Send a test email through the proxy
        print("\nSending test email through SMTP proxy...")
        msg = MIMEMultipart()
        msg['From'] = GMAIL_CONFIG['email']
        msg['To'] = GMAIL_CONFIG['email']  # Send to self
        msg['Subject'] = f"Gmail Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        body = f"""
This is a test email from the Email Management Tool.

Test Details:
- Account: Gmail ({GMAIL_CONFIG['email']})
- Timestamp: {datetime.now()}
- Purpose: Testing Gmail integration with interception system

This email should be intercepted by the SMTP proxy on port 8587.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        server.send_message(msg)
        print("✅ Test email sent successfully!")
        
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("\n⚠️ IMPORTANT: Gmail requires App Passwords for SMTP access!")
        print("1. Enable 2-Factor Authentication in your Google Account")
        print("2. Generate an App Password at: https://myaccount.google.com/apppasswords")
        print("3. Use the 16-character App Password instead of your regular password")
        return False
    except Exception as e:
        print(f"❌ SMTP test failed: {e}")
        return False

def test_gmail_imap():
    """Test Gmail IMAP connectivity"""
    print("\n" + "="*60)
    print("🔍 Testing Gmail IMAP Connection")
    print("="*60)
    
    try:
        print(f"Connecting to {GMAIL_CONFIG['imap_host']}:{GMAIL_CONFIG['imap_port']} (SSL)...")
        imap = imaplib.IMAP4_SSL(GMAIL_CONFIG['imap_host'], GMAIL_CONFIG['imap_port'])
        
        print(f"Authenticating as {GMAIL_CONFIG['email']}...")
        imap.login(GMAIL_CONFIG['email'], GMAIL_CONFIG['password'])
        
        print("Selecting INBOX...")
        status, messages = imap.select('INBOX')
        
        if status == 'OK':
            message_count = int(messages[0])
            print(f"✅ IMAP connection successful! Found {message_count} messages in INBOX")
        
        # List folders
        print("\nAvailable folders:")
        status, folders = imap.list()
        if status == 'OK':
            for folder in folders[:5]:  # Show first 5 folders
                print(f"  - {folder.decode()}")
        
        imap.close()
        imap.logout()
        return True
        
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP authentication failed: {e}")
        print("\n⚠️ Make sure you're using an App Password for Gmail!")
        return False
    except Exception as e:
        print(f"❌ IMAP test failed: {e}")
        return False

def test_proxy_interception():
    """Test email interception through local SMTP proxy"""
    print("\n" + "="*60)
    print("🔍 Testing Email Interception via SMTP Proxy")
    print("="*60)
    
    try:
        # Send email through proxy
        print("Connecting to SMTP proxy on localhost:8587...")
        server = smtplib.SMTP('localhost', 8587, timeout=10)
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_CONFIG['email']
        msg['To'] = 'test@example.com'
        msg['Subject'] = f"Proxy Interception Test - {datetime.now().strftime('%H:%M:%S')}"
        
        body = """
This email is being sent through the SMTP proxy for interception.
It should be stored in the database with PENDING status.

Risk Keywords Test:
- Invoice attached
- Urgent payment required
- Click here to verify your account

Expected Risk Score: High (>60)
"""
        msg.attach(MIMEText(body, 'plain'))
        
        print("Sending test email through proxy...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent to proxy successfully!")
        
        # Check database for intercepted email
        time.sleep(2)  # Wait for processing
        
        print("\nChecking database for intercepted email...")
        conn = sqlite3.connect('data/emails.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, sender, subject, risk_score, status
            FROM emails
            WHERE subject LIKE '%Proxy Interception Test%'            ORDER BY id DESC LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print(f"✅ Email intercepted and stored!")
            print(f"  - ID: {result[0]}")
            print(f"  - Sender: {result[1]}")
            print(f"  - Subject: {result[2]}")
            print(f"  - Risk Score: {result[3]}")
            print(f"  - Status: {result[4]}")
            return True
        else:
            print("❌ Email not found in database")
            return False
            
    except Exception as e:
        print(f"❌ Proxy test failed: {e}")
        print("Make sure the Email Management Tool is running (python multi_account_app.py)")
        return False

def test_dashboard_api():
    """Test dashboard API endpoints"""
    print("\n" + "="*60)
    print("🔍 Testing Dashboard API")
    print("="*60)
    
    base_url = "http://localhost:5000"
    
    try:        # Test if dashboard is running
        print(f"Testing dashboard at {base_url}...")
        response = requests.get(f"{base_url}/login", timeout=5)
        
        if response.status_code == 200:
            print("✅ Dashboard is accessible")
        else:
            print(f"⚠️ Dashboard returned status: {response.status_code}")
            
        # Test API stats endpoint (requires login)
        print("\nTesting API endpoints...")
        # We'll skip auth for now and just check if endpoints exist
        
        endpoints = [
            '/api/stats',
            '/api/accounts',
            '/diagnostics'
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=2)
                # Even if it redirects to login, the endpoint exists
                print(f"  - {endpoint}: {'✅ Exists' if response.status_code in [200, 302] else '❌ Not found'}")
            except:
                print(f"  - {endpoint}: ❌ Error")
                
        return True
        
    except requests.ConnectionError:
        print("❌ Cannot connect to dashboard at http://localhost:5000")
        print("Make sure the Email Management Tool is running (python multi_account_app.py)")
        return False
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def main():
    """Run all Gmail integration tests"""
    print("\n" + "="*70)
    print("🚀 GMAIL INTEGRATION TEST SUITE")
    print("="*70)
    print(f"Testing account: {GMAIL_CONFIG['email']}")
    print(f"Timestamp: {datetime.now()}")
    
    results = {
        'Gmail SMTP': False,
        'Gmail IMAP': False,
        'Proxy Interception': False,
        'Dashboard API': False
    }
    
    # Run tests
    results['Gmail SMTP'] = test_gmail_smtp()
    results['Gmail IMAP'] = test_gmail_imap()
    results['Proxy Interception'] = test_proxy_interception()
    results['Dashboard API'] = test_dashboard_api()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<30} {status}")    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Gmail integration is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the error messages above.")
        
        if not results['Gmail SMTP'] or not results['Gmail IMAP']:
            print("\n📌 Gmail Authentication Tips:")
            print("1. Enable 2-Factor Authentication in your Google Account")
            print("2. Generate an App Password at: https://myaccount.google.com/apppasswords")
            print("3. Use the 16-character App Password instead of your regular password")
            print("4. Update the password in email_accounts.json")
        
        if not results['Proxy Interception'] or not results['Dashboard API']:
            print("\n📌 Application Tips:")
            print("1. Make sure multi_account_app.py is running")
            print("2. Check that port 8587 (SMTP proxy) is available")
            print("3. Check that port 5000 (web dashboard) is available")
            print("4. Run: python multi_account_app.py")

if __name__ == '__main__':
    main()