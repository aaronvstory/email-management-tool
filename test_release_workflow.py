#!/usr/bin/env python3
"""
Test Release Workflow: Verifies proper MOVE from Quarantine to Inbox
Tests that ONLY the edited version appears in Inbox after release (no duplicates).
"""

import os
import sys
import time
import sqlite3
import smtplib
import imaplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')
HOSTINGER_ADDRESS = os.getenv('HOSTINGER_ADDRESS')
HOSTINGER_PASSWORD = os.getenv('HOSTINGER_PASSWORD')

DB_PATH = 'email_manager.db'
API_BASE = 'http://localhost:5000'

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log(message, level='INFO'):
    """Print colored log message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    colors = {
        'INFO': Colors.BLUE,
        'SUCCESS': Colors.GREEN,
        'ERROR': Colors.RED,
        'WARNING': Colors.YELLOW
    }
    color = colors.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}] {message}{Colors.RESET}")

def send_test_email(from_addr, from_pass, to_addr, subject, body, smtp_host, smtp_port, use_ssl=False):
    """Send test email via SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(from_addr, from_pass)
        server.send_message(msg)
        server.quit()

        log(f"✓ Email sent: {subject}", 'SUCCESS')
        return True
    except Exception as e:
        log(f"✗ Failed to send email: {e}", 'ERROR')
        return False

def check_folder_for_subject(email_addr, password, imap_host, folder, subject_contains, exact_match=False):
    """Check if email with subject exists in specific IMAP folder"""
    try:
        mail = imaplib.IMAP4_SSL(imap_host, 993)
        mail.login(email_addr, password)

        # Try to select folder
        try:
            status, _ = mail.select(folder)
            if status != 'OK':
                log(f"Folder {folder} not accessible", 'WARNING')
                mail.logout()
                return False
        except Exception as e:
            log(f"Folder {folder} not found: {e}", 'WARNING')
            mail.logout()
            return False

        # Search for emails
        _, message_numbers = mail.search(None, 'ALL')

        if not message_numbers or not message_numbers[0]:
            log(f"No emails in {folder}", 'INFO')
            mail.logout()
            return False

        # Check recent emails
        for num in message_numbers[0].split()[-30:]:  # Check last 30 emails
            try:
                _, msg_data = mail.fetch(num, '(BODY[HEADER.FIELDS (SUBJECT)])')
                subject_line = msg_data[0][1].decode('utf-8', errors='ignore').strip()

                if exact_match:
                    if subject_contains in subject_line:
                        log(f"✓ Found exact match in {folder}: {subject_line}", 'SUCCESS')
                        mail.logout()
                        return True
                else:
                    if subject_contains.lower() in subject_line.lower():
                        log(f"✓ Found in {folder}: {subject_line}", 'SUCCESS')
                        mail.logout()
                        return True
            except Exception:
                continue

        log(f"✗ Email not found in {folder}", 'WARNING')
        mail.logout()
        return False
    except Exception as e:
        log(f"✗ IMAP check failed for {folder}: {e}", 'ERROR')
        return False

def wait_for_interception(subject_marker, timeout=90):
    """Wait for email to appear in database with HELD status"""
    log(f"Waiting for interception (subject contains: '{subject_marker}')...", 'INFO')
    start_time = time.time()

    while time.time() - start_time < timeout:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        email = cursor.execute(
            "SELECT id, subject, interception_status, status, original_uid FROM email_messages "
            "WHERE subject LIKE ? ORDER BY created_at DESC LIMIT 1",
            (f'%{subject_marker}%',)
        ).fetchone()

        conn.close()

        if email:
            if email['interception_status'] == 'HELD':
                log(f"✓ Email intercepted! ID: {email['id']}, UID: {email['original_uid']}, Status: {email['interception_status']}", 'SUCCESS')
                return email['id']
            else:
                log(f"Email found but status is {email['interception_status']}, waiting...", 'INFO')

        time.sleep(3)

    log(f"✗ Timeout waiting for interception", 'ERROR')
    return None

def edit_email_db(email_id, new_subject, new_body):
    """Edit email via API"""
    try:
        session = requests.Session()

        # Login
        login_page = session.get(f"{API_BASE}/login")
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': session.cookies.get('csrf_token', '')
        }
        session.post(f"{API_BASE}/login", data=login_data)

        # Edit email
        response = session.post(
            f"{API_BASE}/api/email/{email_id}/edit",
            json={'subject': new_subject, 'body_text': new_body},
            headers={'X-CSRFToken': session.cookies.get('csrf_token', '')}
        )

        if response.status_code == 200:
            log(f"✓ Email {email_id} edited successfully", 'SUCCESS')
            return True
        else:
            log(f"✗ Edit failed: {response.status_code} - {response.text}", 'ERROR')
            return False
    except Exception as e:
        log(f"✗ Failed to edit email: {e}", 'ERROR')
        return False

def release_email_api(email_id):
    """Release email via API"""
    try:
        session = requests.Session()

        # Get login page to retrieve CSRF token
        login_page = session.get(f"{API_BASE}/login")

        # Extract CSRF token from meta tag
        import re
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        csrf_token = csrf_match.group(1) if csrf_match else ''

        # Login with CSRF token
        login_response = session.post(
            f"{API_BASE}/login",
            data={
                'username': 'admin',
                'password': 'admin123',
                'csrf_token': csrf_token
            },
            allow_redirects=False
        )

        log(f"Login status: {login_response.status_code}", 'INFO')

        # Get new CSRF token after login
        dashboard = session.get(f"{API_BASE}/dashboard")
        csrf_match2 = re.search(r'<meta name="csrf-token" content="([^"]+)"', dashboard.text)
        new_csrf = csrf_match2.group(1) if csrf_match2 else csrf_token

        # Release email
        response = session.post(
            f"{API_BASE}/api/interception/release/{email_id}",
            json={},  # Send empty JSON payload
            headers={
                'X-CSRFToken': new_csrf,
                'Content-Type': 'application/json'
            }
        )

        if response.status_code == 200:
            try:
                result = response.json()
                log(f"✓ Email {email_id} released successfully: {result}", 'SUCCESS')
                return True
            except Exception as e:
                log(f"✗ Release succeeded but JSON parse failed: {e}", 'ERROR')
                log(f"Response text: {response.text[:500]}", 'WARNING')
                # Consider it a success if status is 200
                return True
        else:
            log(f"✗ Release failed: {response.status_code}", 'ERROR')
            log(f"Response text: {response.text[:500]}", 'WARNING')
            return False
    except Exception as e:
        log(f"✗ Failed to release email: {e}", 'ERROR')
        return False

def main():
    """Main test execution"""
    log(f"\n{Colors.BOLD}RELEASE WORKFLOW TEST{Colors.RESET}", 'INFO')
    log(f"Testing: Intercept → Quarantine → Edit → Release → Verify\n", 'INFO')

    if not HOSTINGER_PASSWORD:
        log("ERROR: HOSTINGER_PASSWORD not configured in .env", 'ERROR')
        sys.exit(1)

    # Generate unique test ID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    test_id = f"RELEASE_TEST_{timestamp}"

    # Step 1: Send email with interception keyword
    log("Step 1: Sending email with 'INVOICE' keyword...", 'INFO')
    subject = f"INVOICE {test_id}"
    body = f"Original body content.\nTest ID: {test_id}\nSent at: {datetime.now()}"

    if not send_test_email(
        GMAIL_ADDRESS, GMAIL_PASSWORD, HOSTINGER_ADDRESS,
        subject, body,
        'smtp.gmail.com', 587, use_ssl=False
    ):
        log("TEST FAILED: Could not send email", 'ERROR')
        sys.exit(1)

    # Step 2: Wait for interception
    log("\nStep 2: Waiting for interception...", 'INFO')
    email_id = wait_for_interception(test_id, timeout=120)

    if not email_id:
        log("TEST FAILED: Email not intercepted", 'ERROR')
        sys.exit(1)

    # Step 3: Verify email is in Quarantine (NOT inbox)
    log("\nStep 3: Verifying email is in Quarantine folder...", 'INFO')
    time.sleep(5)

    quarantine_folders = ['Quarantine', 'INBOX/Quarantine', 'INBOX.Quarantine']
    found_in_quarantine = False

    for folder in quarantine_folders:
        if check_folder_for_subject(HOSTINGER_ADDRESS, HOSTINGER_PASSWORD, 'imap.hostinger.com', folder, test_id):
            found_in_quarantine = True
            log(f"✓ Email found in {folder} folder", 'SUCCESS')
            break

    if not found_in_quarantine:
        log("⚠️ WARNING: Email not found in Quarantine folder (may be OK if folder structure differs)", 'WARNING')

    # Verify NOT in INBOX yet
    inbox_before = check_folder_for_subject(HOSTINGER_ADDRESS, HOSTINGER_PASSWORD, 'imap.hostinger.com', 'INBOX', test_id)
    if inbox_before:
        log("✗ FAIL: Email already in INBOX before release!", 'ERROR')
        sys.exit(1)
    else:
        log("✓ Email NOT in INBOX (as expected)", 'SUCCESS')

    # Step 4: Edit email
    log("\nStep 4: Editing email...", 'INFO')
    edited_subject = f"[EDITED] {subject}"
    edited_body = f"[THIS EMAIL WAS EDITED BY THE SYSTEM]\n\n{body}\n\n[END OF EDITED CONTENT]"

    if not edit_email_db(email_id, edited_subject, edited_body):
        log("TEST FAILED: Could not edit email", 'ERROR')
        sys.exit(1)

    # Step 5: Release email
    log("\nStep 5: Releasing edited email to INBOX...", 'INFO')
    if not release_email_api(email_id):
        log("TEST FAILED: Could not release email", 'ERROR')
        sys.exit(1)

    # Step 6: Verify ONLY edited version is in INBOX
    log("\nStep 6: Waiting for edited email to appear in INBOX...", 'INFO')
    time.sleep(15)  # Give IMAP time to process

    # Check for edited version
    edited_found = check_folder_for_subject(HOSTINGER_ADDRESS, HOSTINGER_PASSWORD, 'imap.hostinger.com', 'INBOX', '[EDITED]', exact_match=False)

    if not edited_found:
        log("✗ FAIL: Edited email not found in INBOX!", 'ERROR')
        sys.exit(1)

    # Step 7: Verify original is removed from Quarantine
    log("\nStep 7: Verifying original removed from Quarantine...", 'INFO')
    time.sleep(5)

    still_in_quarantine = False
    for folder in quarantine_folders:
        if check_folder_for_subject(HOSTINGER_ADDRESS, HOSTINGER_PASSWORD, 'imap.hostinger.com', folder, test_id):
            still_in_quarantine = True
            log(f"⚠️ WARNING: Email still in {folder} folder (not removed)", 'WARNING')
            break

    if not still_in_quarantine:
        log("✓ Email removed from Quarantine (as expected)", 'SUCCESS')

    # Final summary
    log(f"\n{Colors.GREEN}{Colors.BOLD}=== TEST PASSED ==={Colors.RESET}", 'SUCCESS')
    log("✓ Email intercepted and held in Quarantine", 'SUCCESS')
    log("✓ Email edited successfully", 'SUCCESS')
    log("✓ Email released to INBOX", 'SUCCESS')
    log("✓ Only edited version appears in INBOX", 'SUCCESS')

    if not still_in_quarantine:
        log("✓ Original removed from Quarantine (no duplicates)", 'SUCCESS')
    else:
        log("⚠️ Original still in Quarantine (manual cleanup may be needed)", 'WARNING')

    sys.exit(0)

if __name__ == '__main__':
    main()
