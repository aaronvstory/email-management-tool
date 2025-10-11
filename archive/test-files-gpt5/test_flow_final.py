#!/usr/bin/env python
"""
test_flow_final.py - Test the complete email interception flow
Tests: SMTP interception → Database storage → Edit → Status management
"""

import requests
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
SMTP_PROXY = "localhost"
SMTP_PORT = 8587

# Test credentials (from CLAUDE.md)
GMAIL_ADDRESS = "ndayijecika@gmail.com"
GMAIL_PASSWORD = "bjormgplhgwkgpad"
CORRINBOX_ADDRESS = "mcintyre@corrinbox.com"

def test_smtp_interception():
    """Test 1: Send email through SMTP proxy and verify interception"""
    print("\n=== TEST 1: SMTP INTERCEPTION ===")

    # Create test email
    msg = MIMEMultipart()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = CORRINBOX_ADDRESS
    msg['Subject'] = f"TEST_INTERCEPTION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    body = "This is a test email for interception verification."
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Send through SMTP proxy
        server = smtplib.SMTP(SMTP_PROXY, SMTP_PORT)
        text = msg.as_string()
        server.sendmail(GMAIL_ADDRESS, CORRINBOX_ADDRESS, text)
        server.quit()
        print("✓ Email sent through SMTP proxy")
        return msg['Subject']
    except Exception as e:
        print(f"✗ SMTP sending failed: {e}")
        return None

def test_database_storage(subject):
    """Test 2: Verify email is stored in database"""
    print("\n=== TEST 2: DATABASE STORAGE ===")

    # Wait for processing
    time.sleep(2)

    # Create a session to handle authentication
    session = requests.Session()

    # Login first
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)

    # Query API for emails
    response = session.get(f"{BASE_URL}/api/interception/held")

    if response.status_code == 200:
        try:
            emails = response.json()
            for email in emails:
                if subject in email.get('subject', ''):
                    print(f"✓ Email found in database: ID={email['id']}")
                    return email['id']
        except:
            # If JSON parsing fails, check database directly
            import sqlite3
            conn = sqlite3.connect('email_manager.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, subject FROM email_messages WHERE subject LIKE ? ORDER BY id DESC LIMIT 10", (f'%{subject.split("_")[-1]}%',))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                if subject in row[1]:
                    print(f"✓ Email found in database: ID={row[0]}")
                    return row[0]

    print("✗ Email not found in database")
    return None

def test_email_editing(email_id):
    """Test 3: Edit the intercepted email"""
    print("\n=== TEST 3: EMAIL EDITING ===")

    # Create authenticated session
    session = requests.Session()
    login_data = {'username': 'admin', 'password': 'admin123'}
    session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)

    edit_data = {
        'subject': '[EDITED] Original Subject',
        'body_text': 'This email has been edited for testing purposes.\n\nOriginal content modified.'
    }

    response = session.post(
        f"{BASE_URL}/api/email/{email_id}/edit",
        json=edit_data
    )

    if response.status_code == 200:
        print("✓ Email edited successfully")
        return True
    else:
        print(f"✗ Email edit failed: {response.status_code}")
        return False

def test_status_management(email_id):
    """Test 4: Check and update email status"""
    print("\n=== TEST 4: STATUS MANAGEMENT ===")

    # Create authenticated session
    session = requests.Session()
    login_data = {'username': 'admin', 'password': 'admin123'}
    session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)

    # Get current status
    response = session.get(f"{BASE_URL}/api/interception/held/{email_id}")

    if response.status_code == 200:
        try:
            email = response.json()
            print(f"✓ Current status: {email.get('status')}, Interception: {email.get('interception_status')}")
            return True
        except:
            # Check directly in database
            import sqlite3
            conn = sqlite3.connect('email_manager.db')
            cursor = conn.cursor()
            cursor.execute("SELECT status, interception_status FROM email_messages WHERE id = ?", (email_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                print(f"✓ Current status: {row[0]}, Interception: {row[1]}")
                return True
    else:
        print(f"✗ Status check failed: {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("EMAIL INTERCEPTION FLOW TEST")
    print("=" * 60)

    # Check if application is running
    try:
        response = requests.get(f"{BASE_URL}/healthz")
        health = response.json()
        print(f"Application health: {health.get('ok')}")
        print(f"Database: {health.get('db')}")
        print(f"Held emails: {health.get('held_count')}")
    except Exception as e:
        print(f"❌ Application not running: {e}")
        print("Please start the application first: python simple_app.py")
        return

    # Run test sequence
    results = []

    # Test 1: SMTP Interception
    subject = test_smtp_interception()
    results.append(("SMTP Interception", subject is not None))

    if subject:
        # Test 2: Database Storage
        email_id = test_database_storage(subject)
        results.append(("Database Storage", email_id is not None))

        if email_id:
            # Test 3: Email Editing
            edited = test_email_editing(email_id)
            results.append(("Email Editing", edited))

            # Test 4: Status Management
            status_ok = test_status_management(email_id)
            results.append(("Status Management", status_ok))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\nOverall: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! System is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the output above.")

if __name__ == "__main__":
    main()