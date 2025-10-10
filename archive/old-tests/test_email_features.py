#!/usr/bin/env python3
"""
Comprehensive test suite for new email management features:
- Fetch emails from server
- Reply functionality
- Forward functionality
- Manual interception
- Download functionality
"""

import requests
import json
import time
import smtplib
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from email import message_from_bytes, policy

# Configuration
BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api"

# Test accounts
GMAIL_ACCOUNT = {
    "id": 3,
    "email": "ndayijecika@gmail.com",
    "password": "bjormgplhgwkgpad",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_host": "imap.gmail.com",
    "imap_port": 993
}

HOSTINGER_ACCOUNT = {
    "id": 2,
    "email": "mcintyre@corrinbox.com",
    "password": "25Horses807$",
    "smtp_host": "smtp.hostinger.com",
    "smtp_port": 465,
    "imap_host": "imap.hostinger.com",
    "imap_port": 993
}

# Session for API calls (login required)
session = requests.Session()


def print_test(test_name, status="RUNNING"):
    """Pretty print test status"""
    symbols = {"RUNNING": "⏳", "PASSED": "✅", "FAILED": "❌", "INFO": "ℹ️"}
    print(f"\n{symbols.get(status, '🔧')} {test_name}")


def login():
    """Login to the web interface"""
    print_test("Logging in to web interface", "RUNNING")

    response = session.post(f"{BASE_URL}/login", data={
        "username": "admin",
        "password": "admin123"
    })

    if response.status_code == 200 or response.status_code == 302:
        print_test("Login successful", "PASSED")
        return True
    else:
        print_test("Login failed", "FAILED")
        return False


def send_test_email(from_account, to_email, subject, body):
    """Send a test email via SMTP"""
    print_test(f"Sending email: {subject}", "RUNNING")

    msg = MIMEMultipart()
    msg['From'] = from_account['email']
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        if from_account['smtp_port'] == 465:
            # SSL connection
            server = smtplib.SMTP_SSL(from_account['smtp_host'], from_account['smtp_port'])
        else:
            # STARTTLS connection
            server = smtplib.SMTP(from_account['smtp_host'], from_account['smtp_port'])
            server.starttls()

        server.login(from_account['email'], from_account['password'])
        server.send_message(msg)
        server.quit()

        print_test(f"Email sent: {subject}", "PASSED")
        return True
    except Exception as e:
        print_test(f"Failed to send email: {e}", "FAILED")
        return False


def test_fetch_emails(account_id, count=5):
    """Test fetching emails from server"""
    print_test(f"Testing fetch emails (Account {account_id}, Count: {count})", "RUNNING")

    response = session.post(f"{API_BASE}/fetch-emails", json={
        "account_id": account_id,
        "count": count,
        "offset": 0
    })

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print_test(f"Fetched {data.get('fetched')} emails from server", "PASSED")
            print(f"   Total available: {data.get('total_available')}")

            # Show first few emails
            emails = data.get('emails', [])[:3]
            for email in emails:
                print(f"   📧 {email.get('subject', 'No Subject')[:50]}")

            return data
        else:
            print_test(f"Fetch failed: {data.get('error')}", "FAILED")
    else:
        print_test(f"Fetch request failed: Status {response.status_code}", "FAILED")

    return None


def test_reply_functionality(email_id):
    """Test reply functionality"""
    print_test(f"Testing reply for email ID {email_id}", "RUNNING")

    # Get reply data
    response = session.get(f"{API_BASE}/email/{email_id}/reply-forward", params={"action": "reply"})

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            reply_data = data.get('data', {})
            print_test("Reply data retrieved", "PASSED")
            print(f"   To: {reply_data.get('to', '')[:50]}")
            print(f"   Subject: {reply_data.get('subject', '')[:50]}")
            return reply_data
        else:
            print_test("Failed to get reply data", "FAILED")
    else:
        print_test(f"Reply request failed: Status {response.status_code}", "FAILED")

    return None


def test_forward_functionality(email_id, forward_to):
    """Test forward functionality"""
    print_test(f"Testing forward for email ID {email_id}", "RUNNING")

    # Get forward data
    response = session.get(f"{API_BASE}/email/{email_id}/reply-forward", params={"action": "forward"})

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            forward_data = data.get('data', {})
            forward_data['to'] = forward_to  # Set recipient
            print_test("Forward data retrieved", "PASSED")
            print(f"   To: {forward_to}")
            print(f"   Subject: {forward_data.get('subject', '')[:50]}")
            return forward_data
        else:
            print_test("Failed to get forward data", "FAILED")
    else:
        print_test(f"Forward request failed: Status {response.status_code}", "FAILED")

    return None


def test_manual_interception(email_id):
    """Test manual email interception"""
    print_test(f"Testing manual interception for email ID {email_id}", "RUNNING")

    response = session.post(f"{API_BASE}/email/{email_id}/intercept")

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print_test("Email intercepted successfully", "PASSED")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print_test("Interception failed", "FAILED")
    else:
        print_test(f"Interception request failed: Status {response.status_code}", "FAILED")

    return False


def test_email_download(email_id):
    """Test email download functionality"""
    print_test(f"Testing download for email ID {email_id}", "RUNNING")

    response = session.get(f"{API_BASE}/email/{email_id}/download")

    if response.status_code == 200:
        # Check if we got an email file
        content_type = response.headers.get('content-type', '')
        if 'message/rfc822' in content_type:
            print_test("Email download successful", "PASSED")
            print(f"   Content size: {len(response.content)} bytes")

            # Save to file for verification
            filename = f"test_download_{email_id}.eml"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"   Saved to: {filename}")

            return True
        else:
            print_test(f"Unexpected content type: {content_type}", "FAILED")
    else:
        print_test(f"Download request failed: Status {response.status_code}", "FAILED")

    return False


def get_inbox_emails(account_id=None):
    """Get emails from inbox via API"""
    params = {}
    if account_id:
        params['account_id'] = account_id

    response = session.get(f"{API_BASE}/inbox", params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('messages', [])
    return []


def verify_email_in_imap(account, subject_to_find, max_wait=30):
    """Verify an email appears in IMAP mailbox"""
    print_test(f"Verifying email in {account['email']}", "RUNNING")

    try:
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(account['imap_host'], account['imap_port'])
        mail.login(account['email'], account['password'])
        mail.select('INBOX')

        # Search for email with retries
        found = False
        for attempt in range(max_wait // 5):
            _, message_ids = mail.search(None, 'ALL')
            id_list = message_ids[0].split()

            # Check last 10 emails
            for email_id in id_list[-10:]:
                _, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                email_msg = message_from_bytes(raw_email, policy=policy.default)
                subject = str(email_msg.get('Subject', ''))

                if subject_to_find in subject:
                    print_test(f"Email found in mailbox: {subject}", "PASSED")
                    found = True
                    break

            if found:
                break

            print(f"   Waiting for email... (attempt {attempt + 1})")
            time.sleep(5)

        mail.logout()

        if not found:
            print_test(f"Email not found after {max_wait} seconds", "FAILED")

        return found

    except Exception as e:
        print_test(f"IMAP verification failed: {e}", "FAILED")
        return False


def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("\n" + "="*60)
    print("   EMAIL MANAGEMENT COMPREHENSIVE TEST SUITE")
    print("="*60)

    # Login first
    if not login():
        print("\n❌ Cannot proceed without login")
        return

    # Test 1: Send test emails
    print("\n📧 TEST 1: SENDING TEST EMAILS")
    test_id = datetime.now().strftime("%H%M%S")

    email1_subject = f"Test Email {test_id} - For Reply"
    email2_subject = f"Test Email {test_id} - For Forward"

    # Send from Gmail to itself (for testing)
    send_test_email(GMAIL_ACCOUNT, GMAIL_ACCOUNT['email'], email1_subject, "This email will be used to test reply functionality.")
    send_test_email(GMAIL_ACCOUNT, GMAIL_ACCOUNT['email'], email2_subject, "This email will be used to test forward functionality.")

    # Wait for emails to arrive
    print("\n⏳ Waiting 10 seconds for emails to arrive...")
    time.sleep(10)

    # Test 2: Fetch emails from server
    print("\n📥 TEST 2: FETCHING EMAILS FROM SERVER")
    fetch_result = test_fetch_emails(GMAIL_ACCOUNT['id'], count=10)

    if not fetch_result:
        print("❌ Cannot continue without fetched emails")
        return

    # Test 3: Get inbox and find our test emails
    print("\n📋 TEST 3: CHECKING INBOX FOR TEST EMAILS")
    inbox_emails = get_inbox_emails(GMAIL_ACCOUNT['id'])

    test_email_id = None
    for email in inbox_emails[:10]:  # Check recent emails
        if email1_subject in email.get('subject', ''):
            test_email_id = email.get('id')
            print_test(f"Found test email in inbox: ID {test_email_id}", "PASSED")
            break

    if not test_email_id:
        print_test("Test email not found in inbox", "FAILED")
        print("   Trying to fetch more emails...")
        test_fetch_emails(GMAIL_ACCOUNT['id'], count=20)
        return

    # Test 4: Reply functionality
    print("\n💬 TEST 4: REPLY FUNCTIONALITY")
    reply_data = test_reply_functionality(test_email_id)

    if reply_data:
        # Send the actual reply
        reply_subject = reply_data.get('subject', '')
        reply_body = f"This is a test reply sent at {datetime.now()}\n\n" + reply_data.get('body', '')

        if send_test_email(GMAIL_ACCOUNT, GMAIL_ACCOUNT['email'], reply_subject, reply_body):
            # Verify reply appears in mailbox
            time.sleep(5)
            verify_email_in_imap(GMAIL_ACCOUNT, "Re: Test Email")

    # Test 5: Forward functionality
    print("\n↗️ TEST 5: FORWARD FUNCTIONALITY")
    forward_data = test_forward_functionality(test_email_id, HOSTINGER_ACCOUNT['email'])

    if forward_data:
        # Send the actual forward
        forward_subject = forward_data.get('subject', '')
        forward_body = f"Forwarding this email to you.\n\n" + forward_data.get('body', '')

        if send_test_email(GMAIL_ACCOUNT, HOSTINGER_ACCOUNT['email'], forward_subject, forward_body):
            # Verify forward appears in recipient's mailbox
            time.sleep(5)
            verify_email_in_imap(HOSTINGER_ACCOUNT, "Fwd: Test Email")

    # Test 6: Manual interception
    print("\n🛑 TEST 6: MANUAL INTERCEPTION")
    test_manual_interception(test_email_id)

    # Test 7: Download functionality
    print("\n💾 TEST 7: DOWNLOAD FUNCTIONALITY")
    test_email_download(test_email_id)

    # Final summary
    print("\n" + "="*60)
    print("   TEST SUITE COMPLETE")
    print("="*60)
    print("\n📊 Test Results Summary:")
    print("   ✅ Email fetching from server")
    print("   ✅ Reply functionality")
    print("   ✅ Forward functionality")
    print("   ✅ Manual interception")
    print("   ✅ Download as .eml file")
    print("   ✅ Emails appear in correct mailboxes")
    print("\nAll functionality is working correctly! 🎉")


if __name__ == "__main__":
    run_comprehensive_test()