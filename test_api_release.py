#!/usr/bin/env python
"""
test_api_release.py - Complete end-to-end test with release and delivery verification
Tests the complete flow: Send → Intercept → Edit → Release → Verify delivery
"""

import requests
import json
import time
import smtplib
import imaplib
import email
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
CORRINBOX_PASSWORD = "25Horses807$"
CORRINBOX_IMAP = "imap.hostinger.com"
CORRINBOX_IMAP_PORT = 993

def send_test_email():
    """Send a test email through SMTP proxy"""
    print("\n1️⃣ SENDING TEST EMAIL")

    # Create unique test email
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    msg = MIMEMultipart()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = CORRINBOX_ADDRESS
    msg['Subject'] = f"API_RELEASE_TEST_{timestamp}"
    body = f"Test email for API release verification.\nTimestamp: {timestamp}\nThis should be intercepted and edited."
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_PROXY, SMTP_PORT)
        text = msg.as_string()
        server.sendmail(GMAIL_ADDRESS, CORRINBOX_ADDRESS, text)
        server.quit()
        print(f"✓ Email sent: {msg['Subject']}")
        return msg['Subject']
    except Exception as e:
        print(f"✗ Failed to send email: {e}")
        return None

def find_intercepted_email(subject):
    """Find the intercepted email in the system"""
    print("\n2️⃣ FINDING INTERCEPTED EMAIL")

    time.sleep(3)  # Wait for processing

    response = requests.get(f"{BASE_URL}/api/interception/held")

    if response.status_code == 200:
        emails = response.json()
        for email_item in emails:
            if subject in email_item.get('subject', ''):
                print(f"✓ Found email: ID={email_item['id']}, Status={email_item.get('interception_status')}")
                return email_item['id']

    print("✗ Email not found in held queue")
    return None

def edit_email(email_id, original_subject):
    """Edit the intercepted email"""
    print("\n3️⃣ EDITING EMAIL")

    edit_data = {
        'subject': f'[API EDITED] {original_subject}',
        'body_text': '''This email has been edited via API.

--- EDITED CONTENT ---
This is the new content after interception and editing.
The original content has been replaced for testing purposes.

Timestamp: ''' + datetime.now().isoformat()
    }

    response = requests.post(
        f"{BASE_URL}/api/email/{email_id}/edit",
        json=edit_data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        print(f"✓ Email edited successfully")
        return True
    else:
        print(f"✗ Failed to edit email: {response.status_code}")
        if response.text:
            print(f"   Response: {response.text}")
        return False

def release_email(email_id):
    """Release the email to destination"""
    print("\n4️⃣ RELEASING EMAIL")

    response = requests.post(f"{BASE_URL}/api/interception/release/{email_id}")

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Email released: {result.get('message')}")
        return True
    else:
        print(f"✗ Failed to release email: {response.status_code}")
        if response.text:
            print(f"   Response: {response.text}")
        return False

def verify_delivery(subject_pattern, max_attempts=10):
    """Verify the email was delivered to Corrinbox"""
    print("\n5️⃣ VERIFYING DELIVERY")

    try:
        # Connect to Corrinbox IMAP
        mail = imaplib.IMAP4_SSL(CORRINBOX_IMAP, CORRINBOX_IMAP_PORT)
        mail.login(CORRINBOX_ADDRESS, CORRINBOX_PASSWORD)
        mail.select('INBOX')

        # Search for the email
        for attempt in range(max_attempts):
            print(f"   Checking inbox (attempt {attempt + 1}/{max_attempts})...")

            # Search for emails with our pattern
            _, data = mail.search(None, 'ALL')
            email_ids = data[0].split()

            # Check recent emails
            for email_id in reversed(email_ids[-10:]):  # Check last 10 emails
                _, data = mail.fetch(email_id, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                if '[API EDITED]' in msg['Subject'] and subject_pattern in msg['Subject']:
                    print(f"✓ Email delivered to Corrinbox!")
                    print(f"   Subject: {msg['Subject']}")
                    print(f"   From: {msg['From']}")
                    mail.logout()
                    return True

            time.sleep(2)  # Wait before next attempt

        mail.logout()
        print("✗ Email not found in Corrinbox inbox")
        return False

    except Exception as e:
        print(f"✗ Failed to verify delivery: {e}")
        return False

def main():
    """Run complete end-to-end test"""
    print("=" * 70)
    print("COMPLETE API RELEASE TEST - END TO END")
    print("=" * 70)

    # Check application health
    try:
        response = requests.get(f"{BASE_URL}/healthz")
        health = response.json()
        print(f"\n📊 System Status:")
        print(f"   Health: {health.get('ok')}")
        print(f"   Database: {health.get('db')}")
        print(f"   Held emails: {health.get('held_count')}")
    except Exception as e:
        print(f"❌ Application not running: {e}")
        return

    # Run complete test flow
    results = []

    # Step 1: Send email
    subject = send_test_email()
    results.append(("Send Email", subject is not None))

    if subject:
        # Step 2: Find intercepted email
        email_id = find_intercepted_email(subject)
        results.append(("Find Intercepted", email_id is not None))

        if email_id:
            # Step 3: Edit email
            edited = edit_email(email_id, subject)
            results.append(("Edit Email", edited))

            if edited:
                # Step 4: Release email
                released = release_email(email_id)
                results.append(("Release Email", released))

                if released:
                    # Step 5: Verify delivery
                    delivered = verify_delivery(subject)
                    results.append(("Verify Delivery", delivered))

    # Print final results
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    success_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print(f"\n📊 Score: {passed_count}/{total_count} ({success_rate:.0f}%)")

    if passed_count == total_count:
        print("\n🎉 PERFECT! Complete flow working end-to-end!")
        print("✅ Email was sent, intercepted, edited, released, and delivered successfully!")
    else:
        print("\n⚠️ Some steps failed. Check the output above for details.")

if __name__ == "__main__":
    main()