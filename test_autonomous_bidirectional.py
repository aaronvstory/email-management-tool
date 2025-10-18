#!/usr/bin/env python3
"""
Autonomous Bi-Directional Interception Test
Tests Hostinger<->Gmail automatic interception without browser
"""
import requests
import time
import json
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def login():
    """Login to get session cookie"""
    print("\n==> Logging in...")
    session = requests.Session()
    # Get login page first to get CSRF token
    resp = session.get(f"{BASE_URL}/login")
    if resp.status_code != 200:
        print(f"❌ Failed to get login page: {resp.status_code}")
        return None

    # Login with credentials
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    resp = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    if resp.status_code in [200, 302]:
        print("✅ Logged in successfully")
        return session
    else:
        print(f"❌ Login failed: {resp.status_code}")
        return None

def check_watcher_status(session):
    """Check IMAP watcher status"""
    print("\n==> Checking IMAP watcher status...")
    resp = session.get(f"{BASE_URL}/api/watchers/overview")
    if resp.status_code != 200:
        print(f"❌ Failed to get watcher status: {resp.status_code}")
        return False

    data = resp.json()
    if not data.get('accounts'):
        print("❌ No active watchers found")
        return False

    for acc in data['accounts']:
        watcher = acc.get('watcher', {})
        email = acc.get('email_address', 'Unknown')
        state = watcher.get('state', 'stopped')
        last_hb = watcher.get('last_heartbeat', 'Never')
        print(f"   📧 {email}: {state.upper()} (last: {last_hb})")

    return True

def test_send_email(session, direction):
    """Send test email via bi-directional API"""
    print(f"\n==> Testing {direction}...")

    timestamp = datetime.now().strftime("%H:%M:%S")
    subject = f"INVOICE - Test {direction} {timestamp}"

    payload = {
        "direction": direction,
        "subject": subject
    }

    print(f"   Sending email: {subject}")
    resp = session.post(f"{BASE_URL}/api/test/send-bi-directional", json=payload)

    if resp.status_code != 200:
        print(f"❌ Failed to send email: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
        return None, None

    data = resp.json()
    if not data.get('success'):
        print(f"❌ Send failed: {data.get('error', 'Unknown error')}")
        return None, None

    print(f"✅ Email sent successfully")
    print(f"   From: {data.get('sender')}")
    print(f"   To: {data.get('recipient')}")
    return subject, data

def check_interception(session, subject, max_wait=35):
    """Poll for email interception"""
    print(f"\n==> Waiting for interception (max {max_wait}s)...")

    for i in range(max_wait):
        time.sleep(1)

        resp = session.get(f"{BASE_URL}/api/test/check-interception", params={"subject": subject})
        if resp.status_code != 200:
            continue

        data = resp.json()
        if data.get('success') and data.get('email_id'):
            email_id = data['email_id']
            status = data.get('status', 'unknown')
            print(f"✅ Email intercepted after {i+1} seconds!")
            print(f"   Email ID: {email_id}")
            print(f"   Status: {status}")
            return email_id

        if (i + 1) % 5 == 0:
            print(f"   ... waiting ({i+1}s elapsed)")

    print(f"❌ Email NOT intercepted within {max_wait} seconds")
    return None

def verify_in_database(email_id):
    """Verify email in database"""
    print(f"\n==> Verifying email ID {email_id} in database...")
    import sqlite3

    conn = sqlite3.connect('email_manager.db')
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT id, subject, status, interception_status, created_at FROM email_messages WHERE id = ?",
        (email_id,)
    ).fetchone()

    conn.close()

    if row:
        print(f"✅ Email found in database:")
        print(f"   ID: {row[0]}")
        print(f"   Subject: {row[1]}")
        print(f"   Status: {row[2]}")
        print(f"   Interception: {row[3]}")
        print(f"   Created: {row[4]}")
        return True
    else:
        print(f"❌ Email ID {email_id} NOT found in database")
        return False

def main():
    print("=" * 70)
    print("AUTONOMOUS BI-DIRECTIONAL INTERCEPTION TEST")
    print("=" * 70)

    # Login
    session = login()
    if not session:
        print("\n❌ TEST FAILED: Could not login")
        sys.exit(1)

    # Check watchers (skip if fails - not critical)
    try:
        check_watcher_status(session)
    except Exception as e:
        print(f"\n⚠️ WARNING: Watcher status check failed ({str(e)[:50]}), but proceeding...")

    results = {}

    # Test Hostinger -> Gmail
    print("\n" + "=" * 70)
    print("TEST 1: Hostinger → Gmail")
    print("=" * 70)

    subject1, send_data1 = test_send_email(session, "hostinger-to-gmail")
    if subject1:
        email_id1 = check_interception(session, subject1)
        if email_id1:
            db_ok1 = verify_in_database(email_id1)
            results['hostinger-to-gmail'] = {
                'success': True,
                'email_id': email_id1,
                'subject': subject1,
                'verified_in_db': db_ok1
            }
        else:
            results['hostinger-to-gmail'] = {'success': False, 'reason': 'Not intercepted'}
    else:
        results['hostinger-to-gmail'] = {'success': False, 'reason': 'Send failed'}

    # Test Gmail -> Hostinger
    print("\n" + "=" * 70)
    print("TEST 2: Gmail → Hostinger")
    print("=" * 70)

    subject2, send_data2 = test_send_email(session, "gmail-to-hostinger")
    if subject2:
        email_id2 = check_interception(session, subject2)
        if email_id2:
            db_ok2 = verify_in_database(email_id2)
            results['gmail-to-hostinger'] = {
                'success': True,
                'email_id': email_id2,
                'subject': subject2,
                'verified_in_db': db_ok2
            }
        else:
            results['gmail-to-hostinger'] = {'success': False, 'reason': 'Not intercepted'}
    else:
        results['gmail-to-hostinger'] = {'success': False, 'reason': 'Send failed'}

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = all(r.get('success', False) for r in results.values())

    for direction, result in results.items():
        status = "✅ PASS" if result.get('success') else "❌ FAIL"
        print(f"{status} {direction}")
        if result.get('success'):
            print(f"     Email ID: {result.get('email_id')}")
            print(f"     DB Verified: {result.get('verified_in_db')}")
        else:
            print(f"     Reason: {result.get('reason')}")

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()
