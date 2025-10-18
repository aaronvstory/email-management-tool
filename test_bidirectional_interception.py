#!/usr/bin/env python3
"""
Bidirectional Email Interception Test Suite
Tests IMAP-based interception between Gmail and Hostinger accounts.
"""

import os
import sys
import time
import sqlite3
import smtplib
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS', 'ndayijecika@gmail.com')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD', '')
HOSTINGER_ADDRESS = os.getenv('HOSTINGER_ADDRESS', 'mcintyre@corrinbox.com')
HOSTINGER_PASSWORD = os.getenv('HOSTINGER_PASSWORD', '')

DB_PATH = 'email_manager.db'
API_BASE = 'http://localhost:5000'

# Test state
test_results = []
test_emails = []

class Colors:
    """ANSI color codes for terminal output"""
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

def send_email_smtp(from_addr, from_pass, to_addr, subject, body, smtp_host, smtp_port, use_ssl=False):
    """Send email via SMTP"""
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

        log(f"✓ Email sent from {from_addr} to {to_addr}", 'SUCCESS')
        return True
    except Exception as e:
        log(f"✗ Failed to send email: {e}", 'ERROR')
        return False

def check_imap_inbox(email_addr, password, imap_host, subject_contains):
    """Check if email with subject exists in IMAP inbox"""
    try:
        mail = imaplib.IMAP4_SSL(imap_host, 993)
        mail.login(email_addr, password)
        mail.select('INBOX')

        # Search for recent emails
        _, message_numbers = mail.search(None, 'ALL')

        for num in message_numbers[0].split()[-20:]:  # Check last 20 emails
            _, msg_data = mail.fetch(num, '(BODY[HEADER.FIELDS (SUBJECT)])')
            subject_line = msg_data[0][1].decode('utf-8', errors='ignore')

            if subject_contains.lower() in subject_line.lower():
                log(f"✓ Found email in {email_addr} inbox: {subject_line.strip()}", 'SUCCESS')
                mail.close()
                mail.logout()
                return True

        log(f"✗ Email not found in {email_addr} inbox (subject: {subject_contains})", 'WARNING')
        mail.close()
        mail.logout()
        return False
    except Exception as e:
        log(f"✗ IMAP check failed: {e}", 'ERROR')
        return False

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def wait_for_interception(subject_marker, timeout=60):
    """Wait for email to appear in database with HELD status"""
    log(f"Waiting for interception (subject contains: '{subject_marker}')...", 'INFO')
    start_time = time.time()

    while time.time() - start_time < timeout:
        conn = get_db_connection()
        cursor = conn.cursor()

        email = cursor.execute(
            "SELECT id, subject, interception_status, status FROM email_messages "
            "WHERE subject LIKE ? ORDER BY created_at DESC LIMIT 1",
            (f'%{subject_marker}%',)
        ).fetchone()

        conn.close()

        if email:
            if email['interception_status'] == 'HELD':
                log(f"✓ Email intercepted! ID: {email['id']}, Status: {email['interception_status']}", 'SUCCESS')
                return email['id']
            else:
                log(f"Email found but status is {email['interception_status']}, waiting...", 'INFO')

        time.sleep(2)

    log(f"✗ Timeout waiting for interception", 'ERROR')
    return None

def edit_email_db(email_id, new_subject, new_body):
    """Edit email directly in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE email_messages SET subject = ?, body_text = ?, body_html = ? WHERE id = ?",
            (new_subject, new_body, f"<p>{new_body}</p>", email_id)
        )

        conn.commit()
        conn.close()

        log(f"✓ Email {email_id} edited successfully", 'SUCCESS')
        return True
    except Exception as e:
        log(f"✗ Failed to edit email: {e}", 'ERROR')
        return False

def release_email_api(email_id):
    """Release email via API endpoint"""
    import requests
    try:
        # Get CSRF token first
        session = requests.Session()
        login_page = session.get(f"{API_BASE}/login")

        # Login
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': session.cookies.get('csrf_token', '')
        }
        session.post(f"{API_BASE}/login", data=login_data)

        # Release email
        response = session.post(
            f"{API_BASE}/api/interception/release/{email_id}",
            headers={'X-CSRFToken': session.cookies.get('csrf_token', '')}
        )

        if response.status_code == 200:
            log(f"✓ Email {email_id} released successfully", 'SUCCESS')
            return True
        else:
            log(f"✗ Release failed: {response.status_code} - {response.text}", 'ERROR')
            return False
    except Exception as e:
        log(f"✗ Failed to release email: {e}", 'ERROR')
        return False

def run_test(test_name, from_addr, from_pass, to_addr, smtp_host, smtp_port, use_ssl,
             imap_host, imap_pass, include_keyword=False):
    """Run a complete interception test"""
    log(f"\n{'='*60}", 'INFO')
    log(f"{Colors.BOLD}Starting Test: {test_name}{Colors.RESET}", 'INFO')
    log(f"{'='*60}", 'INFO')

    # Generate unique subject
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    subject_marker = f"TEST_{timestamp}"

    if include_keyword:
        subject = f"INVOICE {subject_marker}"
        body = f"This is a test email with invoice keyword.\nTest ID: {subject_marker}\nSent at: {datetime.now()}"
    else:
        subject = f"Normal Email {subject_marker}"
        body = f"This is a normal test email without keywords.\nTest ID: {subject_marker}\nSent at: {datetime.now()}"

    # Step 1: Send email
    log(f"Step 1: Sending email from {from_addr} to {to_addr}", 'INFO')
    if not send_email_smtp(from_addr, from_pass, to_addr, subject, body, smtp_host, smtp_port, use_ssl):
        test_results.append({'test': test_name, 'status': 'FAIL', 'reason': 'Failed to send email'})
        return False

    time.sleep(5)  # Wait for processing

    if include_keyword:
        # Step 2: Wait for interception
        log(f"Step 2: Waiting for interception...", 'INFO')
        email_id = wait_for_interception(subject_marker, timeout=90)

        if not email_id:
            test_results.append({'test': test_name, 'status': 'FAIL', 'reason': 'Email not intercepted'})
            return False

        # Step 3: Edit email
        log(f"Step 3: Editing intercepted email...", 'INFO')
        edited_subject = f"[EDITED] {subject}"
        edited_body = f"[THIS EMAIL WAS EDITED]\n\n{body}\n\n[END OF EDITED CONTENT]"

        if not edit_email_db(email_id, edited_subject, edited_body):
            test_results.append({'test': test_name, 'status': 'FAIL', 'reason': 'Failed to edit email'})
            return False

        # Step 4: Release email
        log(f"Step 4: Releasing edited email...", 'INFO')
        if not release_email_api(email_id):
            test_results.append({'test': test_name, 'status': 'FAIL', 'reason': 'Failed to release email'})
            return False

        time.sleep(10)  # Wait for IMAP APPEND

        # Step 5: Verify edited version in inbox
        log(f"Step 5: Verifying edited email in inbox...", 'INFO')
        if check_imap_inbox(to_addr, imap_pass, imap_host, "[EDITED]"):
            log(f"✓ Edited email found in inbox!", 'SUCCESS')
            test_results.append({'test': test_name, 'status': 'PASS', 'email_id': email_id})
            return True
        else:
            log(f"✗ Edited email not found in inbox", 'ERROR')
            test_results.append({'test': test_name, 'status': 'FAIL', 'reason': 'Edited email not in inbox'})
            return False
    else:
        # Control test: Should NOT be intercepted
        log(f"Step 2: Waiting to verify email is NOT intercepted...", 'INFO')
        time.sleep(30)  # Give time for potential interception

        # Check if it went directly to inbox
        log(f"Step 3: Verifying email delivered to inbox (not intercepted)...", 'INFO')
        if check_imap_inbox(to_addr, imap_pass, imap_host, subject_marker):
            log(f"✓ Email delivered normally without interception!", 'SUCCESS')
            test_results.append({'test': test_name, 'status': 'PASS'})
            return True
        else:
            log(f"✗ Email not found in inbox", 'ERROR')
            test_results.append({'test': test_name, 'status': 'FAIL', 'reason': 'Email not delivered'})
            return False

def print_summary():
    """Print test summary"""
    log(f"\n{'='*60}", 'INFO')
    log(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}", 'INFO')
    log(f"{'='*60}", 'INFO')

    total = len(test_results)
    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = total - passed

    for result in test_results:
        status_color = Colors.GREEN if result['status'] == 'PASS' else Colors.RED
        status_icon = '✓' if result['status'] == 'PASS' else '✗'
        log(f"{status_icon} {result['test']}: {status_color}{result['status']}{Colors.RESET}", 'INFO')
        if 'reason' in result:
            log(f"  Reason: {result['reason']}", 'WARNING')

    log(f"\nTotal: {total} | Passed: {Colors.GREEN}{passed}{Colors.RESET} | Failed: {Colors.RED}{failed}{Colors.RESET}", 'INFO')
    log(f"{'='*60}\n", 'INFO')

def main():
    """Main test execution"""
    log(f"\n{Colors.BOLD}BIDIRECTIONAL EMAIL INTERCEPTION TEST SUITE{Colors.RESET}", 'INFO')
    log(f"Testing IMAP-based interception between Gmail and Hostinger\n", 'INFO')

    # Verify credentials
    if not GMAIL_PASSWORD or not HOSTINGER_PASSWORD:
        log("ERROR: Email credentials not configured in .env file", 'ERROR')
        sys.exit(1)

    # Test 1: Gmail → Hostinger WITHOUT keyword (control)
    run_test(
        "Test 1: Gmail → Hostinger (NO keyword)",
        GMAIL_ADDRESS, GMAIL_PASSWORD, HOSTINGER_ADDRESS,
        'smtp.gmail.com', 587, False,
        'imap.hostinger.com', HOSTINGER_PASSWORD,
        include_keyword=False
    )

    # Test 2: Gmail → Hostinger WITH keyword (intercept)
    run_test(
        "Test 2: Gmail → Hostinger (WITH 'invoice')",
        GMAIL_ADDRESS, GMAIL_PASSWORD, HOSTINGER_ADDRESS,
        'smtp.gmail.com', 587, False,
        'imap.hostinger.com', HOSTINGER_PASSWORD,
        include_keyword=True
    )

    # Test 3: Hostinger → Gmail WITHOUT keyword (control)
    run_test(
        "Test 3: Hostinger → Gmail (NO keyword)",
        HOSTINGER_ADDRESS, HOSTINGER_PASSWORD, GMAIL_ADDRESS,
        'smtp.hostinger.com', 465, True,
        'imap.gmail.com', GMAIL_PASSWORD,
        include_keyword=False
    )

    # Test 4: Hostinger → Gmail WITH keyword (intercept)
    run_test(
        "Test 4: Hostinger → Gmail (WITH 'invoice')",
        HOSTINGER_ADDRESS, HOSTINGER_PASSWORD, GMAIL_ADDRESS,
        'smtp.hostinger.com', 465, True,
        'imap.gmail.com', GMAIL_PASSWORD,
        include_keyword=True
    )

    # Print summary
    print_summary()

    # Exit with appropriate code
    sys.exit(0 if all(r['status'] == 'PASS' for r in test_results) else 1)

if __name__ == '__main__':
    main()
