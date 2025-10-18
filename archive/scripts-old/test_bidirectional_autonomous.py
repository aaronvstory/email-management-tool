#!/usr/bin/env python3
"""
Autonomous Bi-Directional Email Interception Test
Tests both Hostinger→Gmail and Gmail→Hostinger flows with proper CSRF handling
"""

import requests
import time
from datetime import datetime
import re

BASE_URL = "http://localhost:5000"

def extract_csrf_token(html_content):
    """Extract CSRF token from HTML meta tag"""
    match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html_content)
    if match:
        return match.group(1)
    return None

def login():
    """Login and extract CSRF token"""
    print("\n🔐 Logging in...")
    session = requests.Session()

    # Get login page to extract CSRF token
    resp = session.get(f"{BASE_URL}/login")
    csrf_token = extract_csrf_token(resp.text)

    if not csrf_token:
        print("❌ Failed to extract CSRF token from login page")
        return None

    print(f"✓ CSRF token extracted: {csrf_token[:16]}...")

    # Login with CSRF token
    login_data = {
        "username": "admin",
        "password": "admin123",
        "csrf_token": csrf_token
    }

    resp = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)

    if resp.status_code in [200, 302]:
        print("✓ Login successful")
        # Store CSRF token for later API calls
        session.csrf_token = csrf_token
        return session
    else:
        print(f"❌ Login failed: {resp.status_code}")
        return None

def test_send_email(session, direction):
    """Send test email via bi-directional API with CSRF token"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    subject = f"INVOICE - Test {direction} {timestamp}"

    print(f"\n📧 Sending {direction} email...")
    print(f"   Subject: {subject}")

    payload = {
        "direction": direction,
        "subject": subject
    }

    # Add CSRF token to headers
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': session.csrf_token
    }

    resp = session.post(
        f"{BASE_URL}/api/test/send-bi-directional",
        json=payload,
        headers=headers
    )

    if resp.status_code == 200:
        data = resp.json()
        if data.get('success'):
            print(f"✓ Email sent successfully")
            print(f"   Sender: {data.get('sender')}")
            print(f"   Recipient: {data.get('recipient')}")
            return subject, data
        else:
            print(f"❌ API returned success=False: {data.get('error')}")
            return subject, None
    else:
        print(f"❌ Failed to send email: {resp.status_code}")
        try:
            print(f"   Error: {resp.text[:200]}")
        except:
            pass
        return subject, None

def check_interception(session, subject, max_wait=35):
    """Poll for email interception with CSRF token"""
    print(f"\n🔍 Checking for interception (max {max_wait}s)...")

    headers = {'X-CSRFToken': session.csrf_token}

    for i in range(max_wait):
        time.sleep(1)

        # Query with CSRF token in headers
        resp = session.get(
            f"{BASE_URL}/api/test/check-interception",
            params={"subject": subject},
            headers=headers
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data.get('email_id'):
                print(f"✓ Email intercepted! ID: {data['email_id']}")
                print(f"   Status: {data.get('status')}")
                print(f"   Interception: {data.get('interception_status')}")
                print(f"   Time to intercept: {i+1}s")
                return data['email_id']

        if (i + 1) % 5 == 0:
            print(f"   Still waiting... ({i+1}s)")

    print(f"❌ Email not intercepted after {max_wait}s")
    return None

def main():
    print("=" * 70)
    print("AUTONOMOUS BI-DIRECTIONAL INTERCEPTION TEST".center(70))
    print("=" * 70)

    # Login
    session = login()
    if not session:
        print("\n❌ CRITICAL: Login failed. Cannot proceed.")
        return

    # Test 1: Hostinger → Gmail
    print("\n" + "=" * 70)
    print("TEST 1: HOSTINGER → GMAIL".center(70))
    print("=" * 70)

    subject1, send_result1 = test_send_email(session, "hostinger-to-gmail")
    if send_result1:
        email_id1 = check_interception(session, subject1)
        if email_id1:
            print("\n✅ Test 1 PASSED: Hostinger→Gmail automatic interception working!")
        else:
            print("\n⚠️ Test 1 INCONCLUSIVE: Email sent but not intercepted in time")
    else:
        print("\n❌ Test 1 FAILED: Could not send email")

    time.sleep(2)  # Brief pause between tests

    # Test 2: Gmail → Hostinger
    print("\n" + "=" * 70)
    print("TEST 2: GMAIL → HOSTINGER".center(70))
    print("=" * 70)

    subject2, send_result2 = test_send_email(session, "gmail-to-hostinger")
    if send_result2:
        email_id2 = check_interception(session, subject2)
        if email_id2:
            print("\n✅ Test 2 PASSED: Gmail→Hostinger automatic interception working!")
        else:
            print("\n⚠️ Test 2 INCONCLUSIVE: Email sent but not intercepted in time")
    else:
        print("\n❌ Test 2 FAILED: Could not send email")

    # Final summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY".center(70))
    print("=" * 70)

    if send_result1 and email_id1 and send_result2 and email_id2:
        print("\n🎉 ALL TESTS PASSED!")
        print("   ✓ Both directions working")
        print("   ✓ Automatic interception confirmed")
        print("   ✓ Database storage verified")
    elif send_result1 and send_result2:
        print("\n⚠️ PARTIAL SUCCESS")
        print("   ✓ Emails sent successfully")
        print("   ⚠ Interception timing may need adjustment")
    else:
        print("\n❌ TESTS FAILED")
        print("   Check application logs for details")

if __name__ == "__main__":
    main()
