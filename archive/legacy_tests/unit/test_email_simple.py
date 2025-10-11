#!/usr/bin/env python3
"""
Simple Email Test - Works without Gmail
Tests the Email Management Tool with local SMTP proxy only
"""

import smtplib
import sqlite3
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_local_smtp_proxy():
    """Test email interception through local SMTP proxy only"""
    print("\n" + "="*60)
    print("🔍 Testing Local SMTP Proxy (No External Email Required)")
    print("="*60)
    
    try:
        # Connect to local SMTP proxy
        print("Connecting to SMTP proxy on localhost:8587...")
        server = smtplib.SMTP('localhost', 8587, timeout=10)
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = 'test@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = f"Local Proxy Test - {datetime.now().strftime('%H:%M:%S')}"
        
        body = """
This is a test email sent through the local SMTP proxy.
No external email account is required for this test.

Risk Keywords Test:
- Urgent: Please respond immediately
- Payment: Invoice #12345 attached
- Password: Reset your account password
- Click here: Verify your account

Expected Risk Score: High (>60)
"""
        msg.attach(MIMEText(body, 'plain'))
        
        print("Sending test email through proxy...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent to proxy successfully!")
        
        # Wait for processing
        time.sleep(2)
        
        # Check database
        print("\nChecking database for intercepted email...")
        conn = sqlite3.connect('data/emails.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, sender, recipient, subject, risk_score, status
            FROM emails
            ORDER BY id DESC
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print("✅ Email successfully intercepted and stored!")
            print(f"  - ID: {result[0]}")
            print(f"  - From: {result[1]}")
            print(f"  - To: {result[2]}")
            print(f"  - Subject: {result[3]}")
            print(f"  - Risk Score: {result[4]}")
            print(f"  - Status: {result[5]}")
            
            if result[4] > 60:
                print("  - ✅ Risk scoring working correctly (High risk detected)")
            
            return True
        else:
            print("❌ Email not found in database")
            return False
            
    except ConnectionRefusedError:
        print("❌ Cannot connect to SMTP proxy on localhost:8587")
        print("\nTo fix this:")
        print("1. Start the Email Management Tool:")
        print("   python multi_account_app.py")
        print("2. Or use the batch file:")
        print("   start_multi_account.bat")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_dashboard_access():
    """Test if dashboard is accessible"""
    print("\n" + "="*60)
    print("🔍 Testing Dashboard Access")
    print("="*60)
    
    try:
        import requests
        response = requests.get('http://localhost:5000/login', timeout=5)
        
        if response.status_code == 200:
            print("✅ Dashboard is accessible at http://localhost:5000")
            print("   Default login: admin / admin123")
            return True
        else:
            print(f"⚠️ Dashboard returned status: {response.status_code}")
            return False
    except:
        print("❌ Dashboard not accessible")
        print("   Make sure the application is running")
        return False

def main():
    print("\n" + "="*70)
    print("🚀 EMAIL MANAGEMENT TOOL - LOCAL TEST")
    print("="*70)
    print("This test works WITHOUT external email accounts")
    print("It only tests the local SMTP proxy and interception")
    
    # Run tests
    proxy_test = test_local_smtp_proxy()
    dashboard_test = test_dashboard_access()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    print(f"SMTP Proxy Interception: {'✅ PASSED' if proxy_test else '❌ FAILED'}")
    print(f"Dashboard Access: {'✅ PASSED' if dashboard_test else '❌ FAILED'}")
    
    if proxy_test and dashboard_test:
        print("\n✅ System is working correctly!")
        print("\nNext steps:")
        print("1. Access dashboard at http://localhost:5000")
        print("2. Login with admin / admin123")
        print("3. View intercepted emails in the Emails section")
        print("4. Add Gmail account after enabling 2FA (see GMAIL_SETUP_GUIDE.md)")
    else:
        print("\n⚠️ Some tests failed. Make sure the application is running:")
        print("   python multi_account_app.py")

if __name__ == '__main__':
    main()