#!/usr/bin/env python3
"""
Test Hybrid IMAP Strategy - Bi-Directional Email Interception
Verifies the hybrid IDLE+polling implementation works with real emails
"""
import requests
import time
import sqlite3
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def send_test_email(direction):
    """Send test email via bi-directional API"""
    session = requests.Session()

    # Login first
    print(f"\n{'='*70}")
    print(f"TEST: {direction}")
    print(f"{'='*70}")

    login_resp = session.post(f"{BASE_URL}/login", data={
        "username": "admin",
        "password": "admin123"
    }, allow_redirects=False)

    if login_resp.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_resp.status_code}")
        return None

    print("✅ Logged in successfully")

    # Send email
    timestamp = datetime.now().strftime("%H:%M:%S")
    subject = f"HYBRID TEST - {direction} {timestamp}"

    # Get CSRF token from login page
    csrf_resp = session.get(f"{BASE_URL}/login")

    # Try sending with session cookies
    send_resp = session.post(
        f"{BASE_URL}/api/test/send-bi-directional",
        json={"direction": direction, "subject": subject},
        headers={"Content-Type": "application/json"}
    )

    if send_resp.status_code != 200:
        print(f"❌ Send failed: {send_resp.status_code}")
        print(f"   Response: {send_resp.text[:200]}")
        return None

    data = send_resp.json()
    if not data.get('success'):
        print(f"❌ Send failed: {data.get('error')}")
        return None

    print(f"✅ Email sent successfully")
    print(f"   Subject: {subject}")
    print(f"   From: {data.get('sender')}")
    print(f"   To: {data.get('recipient')}")

    return subject

def wait_for_interception(subject, max_wait=45):
    """Poll database for email interception"""
    print(f"\n⏳ Waiting for interception (max {max_wait}s)...")

    conn = sqlite3.connect('email_manager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    for i in range(max_wait):
        time.sleep(1)

        row = cursor.execute(
            "SELECT id, subject, status, interception_status, created_at FROM email_messages WHERE subject=? ORDER BY created_at DESC LIMIT 1",
            (subject,)
        ).fetchone()

        if row:
            print(f"\n✅ EMAIL INTERCEPTED after {i+1} seconds!")
            print(f"   ID: {row['id']}")
            print(f"   Subject: {row['subject']}")
            print(f"   Status: {row['status']}")
            print(f"   Interception: {row['interception_status']}")
            print(f"   Created: {row['created_at']}")
            conn.close()
            return True

        if (i + 1) % 10 == 0:
            print(f"   ... waiting ({i+1}s elapsed)")

    print(f"\n❌ EMAIL NOT INTERCEPTED within {max_wait} seconds")
    conn.close()
    return False

def check_watcher_status():
    """Check current IMAP watcher status"""
    print(f"\n{'='*70}")
    print("IMAP WATCHER STATUS")
    print(f"{'='*70}")

    conn = sqlite3.connect('email_manager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows = cursor.execute(
        "SELECT worker_id, status, last_heartbeat FROM worker_heartbeats WHERE worker_id LIKE 'imap_%' ORDER BY last_heartbeat DESC"
    ).fetchall()

    for row in rows:
        print(f"   {row['worker_id']}: {row['status'].upper()} (last: {row['last_heartbeat']})")

    conn.close()

def main():
    print(f"\n{'='*70}")
    print("HYBRID IMAP STRATEGY - BI-DIRECTIONAL INTERCEPTION TEST")
    print(f"{'='*70}")

    check_watcher_status()

    # Test 1: Hostinger → Gmail
    subject1 = send_test_email("hostinger-to-gmail")
    if subject1:
        result1 = wait_for_interception(subject1)
    else:
        result1 = False

    time.sleep(2)  # Brief pause between tests

    # Test 2: Gmail → Hostinger
    subject2 = send_test_email("gmail-to-hostinger")
    if subject2:
        result2 = wait_for_interception(subject2)
    else:
        result2 = False

    # Summary
    print(f"\n{'='*70}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"   Hostinger → Gmail: {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"   Gmail → Hostinger: {'✅ PASS' if result2 else '❌ FAIL'}")

    if result1 and result2:
        print(f"\n{'='*70}")
        print("✅ ALL TESTS PASSED - Hybrid IMAP strategy is working!")
        print(f"{'='*70}")
    else:
        print(f"\n{'='*70}")
        print("❌ SOME TESTS FAILED")
        print(f"{'='*70}")

    check_watcher_status()

if __name__ == "__main__":
    main()
