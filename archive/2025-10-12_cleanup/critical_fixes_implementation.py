#!/usr/bin/env python3
"""
Critical fixes implementation for Email Management Tool
Addresses header preservation, database backup, error handling, and verification
"""

import os
import sqlite3
import shutil
import time
import socket
import logging
from datetime import datetime
from contextlib import contextmanager
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.parser import BytesParser
from email.policy import default as default_policy

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DB_PATH = "email_manager.db"
BACKUP_DIR = "database_backups"

# ============================================================================
# CRITICAL FIX 1: Database Backup Before Critical Operations
# ============================================================================

@contextmanager
def database_backup(operation_name="operation"):
    """
    Create database backup before critical operations.
    Automatically restores on failure.
    """
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{operation_name}_{timestamp}.db")

    try:
        # Create backup
        shutil.copy2(DB_PATH, backup_path)
        log.info(f"Database backed up to {backup_path}")

        yield backup_path

        # Clean old backups (keep last 10)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))

    except Exception as e:
        # Restore from backup on failure
        log.error(f"Operation failed: {e}. Restoring database from backup.")
        shutil.copy2(backup_path, DB_PATH)
        raise

# ============================================================================
# CRITICAL FIX 2: Port Conflict Detection and Handling
# ============================================================================

def find_available_port(start_port=8587, max_attempts=10):
    """
    Find an available port starting from start_port.
    Kill existing process or find new port.
    """
    import psutil

    for port_offset in range(max_attempts):
        port = start_port + port_offset

        # Check if port is in use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result != 0:  # Port is free
            return port

        # Port is in use - try to kill the process
        if port_offset == 0:  # Only kill on original port
            log.warning(f"Port {port} is in use. Attempting to free it...")
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    for conn in proc.connections('inet'):
                        if conn.laddr.port == port:
                            log.info(f"Killing process {proc.pid} using port {port}")
                            proc.kill()
                            time.sleep(2)  # Wait for process to die
                            return port
            except Exception as e:
                log.warning(f"Could not kill process on port {port}: {e}")

    raise RuntimeError(f"No available ports found starting from {start_port}")

# ============================================================================
# CRITICAL FIX 3: Verify Email Release to Inbox
# ============================================================================

def verify_email_in_inbox(imap_host, imap_port, username, password, message_id, timeout=30):
    """
    Verify that a released email actually appears in the recipient's inbox.
    Returns True if found, False if not found within timeout.
    """
    start_time = time.time()

    try:
        # Connect to IMAP
        if int(imap_port) == 993:
            imap = imaplib.IMAP4_SSL(imap_host, int(imap_port))
        else:
            imap = imaplib.IMAP4(imap_host, int(imap_port))

        imap.login(username, password)

        # Poll inbox for the message
        while time.time() - start_time < timeout:
            imap.select('INBOX')

            # Search by Message-ID
            typ, data = imap.search(None, 'HEADER', 'Message-ID', f'"{message_id}"')

            if typ == 'OK' and data[0]:
                uids = data[0].split()
                if uids:
                    log.info(f"✅ Email verified in inbox! Message-ID: {message_id}")
                    imap.logout()
                    return True

            time.sleep(2)  # Wait before next check

        imap.logout()
        log.warning(f"⚠️ Email not found in inbox after {timeout}s. Message-ID: {message_id}")
        return False

    except Exception as e:
        log.error(f"Failed to verify email in inbox: {e}")
        return False

# ============================================================================
# CRITICAL FIX 4: Preserve Headers (Only Edit Body/Subject)
# ============================================================================

def edit_email_preserve_headers(raw_email_bytes, new_subject=None, new_body=None):
    """
    Edit email while preserving ALL headers except Subject.
    Message-ID and other headers remain completely unchanged.
    """
    msg = BytesParser(policy=default_policy).parsebytes(raw_email_bytes)

    # Store original Message-ID (MUST be preserved)
    original_message_id = msg.get('Message-ID')

    # Only modify subject if provided
    if new_subject is not None:
        if msg['Subject']:
            msg.replace_header('Subject', new_subject)
        else:
            msg.add_header('Subject', new_subject)

    # Only modify body if provided
    if new_body is not None:
        if msg.is_multipart():
            # Find and replace text/plain part
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    part.set_content(new_body)
                    break
        else:
            # Single part message
            msg.set_content(new_body)

    # Verify Message-ID unchanged
    if msg.get('Message-ID') != original_message_id:
        raise ValueError("CRITICAL: Message-ID was altered! This must never happen!")

    return msg.as_bytes()

# ============================================================================
# CRITICAL FIX 5: Bounce/Reject Notification System
# ============================================================================

class EmailNotificationSystem:
    """Prominent notification system for bounced/rejected emails"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def notify_bounce(self, email_id, bounce_reason, user_id=None):
        """
        Create prominent notification for bounced email.
        Stores in database and triggers UI alert.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Create notifications table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER,
                    notification_type TEXT,
                    severity TEXT,
                    message TEXT,
                    user_id INTEGER,
                    acknowledged BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert critical notification
            cursor.execute("""
                INSERT INTO email_notifications
                (email_id, notification_type, severity, message, user_id)
                VALUES (?, 'BOUNCE', 'CRITICAL', ?, ?)
            """, (email_id, f"Email bounced: {bounce_reason}", user_id))

            # Update email status
            cursor.execute("""
                UPDATE email_messages
                SET status = 'BOUNCED',
                    bounce_reason = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (bounce_reason, email_id))

            conn.commit()
            log.critical(f"🔴 BOUNCE NOTIFICATION: Email {email_id} bounced - {bounce_reason}")

            # Trigger SSE notification (if available)
            self._trigger_sse_notification(email_id, "bounce", bounce_reason)

        finally:
            conn.close()

    def _trigger_sse_notification(self, email_id, event_type, message):
        """Send real-time notification via SSE"""
        # This would integrate with the SSE endpoint
        # For now, just log it prominently
        print(f"\n{'='*60}")
        print(f"⚠️  CRITICAL EMAIL EVENT: {event_type.upper()}")
        print(f"📧 Email ID: {email_id}")
        print(f"📝 Message: {message}")
        print(f"{'='*60}\n")

# ============================================================================
# CRITICAL FIX 6: SMTP Proxy Error Handling
# ============================================================================

class SafeSMTPHandler:
    """SMTP handler with guaranteed database write and error recovery"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    async def handle_DATA(self, server, session, envelope):
        """
        Handle incoming email with multiple safety layers.
        Ensures email is never lost even if database write fails.
        """
        import json

        # Create emergency backup first
        emergency_dir = "emergency_email_backup"
        os.makedirs(emergency_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        emergency_file = os.path.join(emergency_dir, f"email_{timestamp}.json")

        # Save raw email to emergency backup
        email_data = {
            'from': envelope.mail_from,
            'to': envelope.rcpt_tos,
            'data': envelope.content.decode('utf-8', errors='ignore'),
            'timestamp': timestamp
        }

        try:
            with open(emergency_file, 'w') as f:
                json.dump(email_data, f)

            # Now attempt database write with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()

                    # Parse email
                    from email import message_from_bytes
                    msg = message_from_bytes(envelope.content)

                    # Extract fields
                    subject = msg.get('Subject', 'No Subject')
                    sender = envelope.mail_from
                    recipients = json.dumps(envelope.rcpt_tos)
                    message_id = msg.get('Message-ID', f'smtp_{timestamp}')

                    # Insert to database
                    cursor.execute("""
                        INSERT INTO email_messages
                        (message_id, sender, recipients, subject, raw_content,
                         status, interception_status, created_at)
                        VALUES (?, ?, ?, ?, ?, 'PENDING', 'HELD', datetime('now'))
                    """, (message_id, sender, recipients, subject, envelope.content))

                    conn.commit()
                    conn.close()

                    # Success - remove emergency backup
                    os.remove(emergency_file)
                    log.info(f"Email intercepted successfully: {subject}")
                    break

                except Exception as e:
                    log.error(f"Database write attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        log.critical(f"Failed to save email to database! Emergency backup at: {emergency_file}")
                        # Email remains in emergency backup for manual recovery
                    else:
                        time.sleep(1)  # Wait before retry

        except Exception as e:
            log.critical(f"Critical failure in SMTP handler: {e}")
            log.critical(f"Email saved to emergency backup: {emergency_file}")

        return '250 Message accepted for delivery'

# ============================================================================
# INTEGRATION TEST: Verify Complete Flow
# ============================================================================

def integration_test_email_release():
    """
    Integration test that verifies:
    1. Email is intercepted and held
    2. Email can be edited preserving headers
    3. Email appears in inbox after release
    """
    import requests
    from bs4 import BeautifulSoup

    print("\n" + "="*80)
    print("INTEGRATION TEST: Email Release Verification")
    print("="*80 + "\n")

    test_results = {
        'intercept': False,
        'edit_preserves_headers': False,
        'appears_in_inbox': False,
        'database_backup': False
    }

    try:
        # Test 1: Database backup
        print("1. Testing database backup mechanism...")
        with database_backup("test_operation") as backup_path:
            if os.path.exists(backup_path):
                test_results['database_backup'] = True
                print("   ✅ Database backup created successfully")

        # Test 2: Send test email
        print("\n2. Sending test email through SMTP proxy...")
        unique_id = f"TEST_{int(time.time())}"
        test_msg = MIMEMultipart()
        test_msg['From'] = "test@example.com"
        test_msg['To'] = "ndayijecika@gmail.com"
        test_msg['Subject'] = f"Integration Test {unique_id}"
        test_msg['Message-ID'] = f"<{unique_id}@test.example.com>"
        test_msg.attach(MIMEText("Original body text", 'plain'))

        original_message_id = test_msg['Message-ID']

        # Send through SMTP proxy
        with smtplib.SMTP('localhost', 8587) as smtp:
            smtp.send_message(test_msg)

        time.sleep(2)

        # Test 3: Verify intercepted
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, message_id, subject, body_text, raw_content
            FROM email_messages
            WHERE message_id = ?
        """, (original_message_id,))

        row = cursor.fetchone()
        if row:
            test_results['intercept'] = True
            email_id = row[0]
            print(f"   ✅ Email intercepted with ID: {email_id}")

            # Test 4: Edit while preserving headers
            print("\n3. Testing header preservation during edit...")
            raw_content = row[4]
            if raw_content:
                edited = edit_email_preserve_headers(
                    raw_content.encode('utf-8') if isinstance(raw_content, str) else raw_content,
                    new_subject=f"EDITED {unique_id}",
                    new_body="Edited body text"
                )

                # Parse edited email
                from email import message_from_bytes
                edited_msg = message_from_bytes(edited)

                # Verify Message-ID unchanged
                if edited_msg.get('Message-ID') == original_message_id:
                    test_results['edit_preserves_headers'] = True
                    print(f"   ✅ Message-ID preserved: {original_message_id}")
                else:
                    print(f"   ❌ Message-ID changed!")

            # Test 5: Release and verify in inbox
            print("\n4. Releasing email and verifying inbox delivery...")

            # Simulate release via API
            session = requests.Session()
            # Login first
            login_resp = session.post("http://localhost:5000/login", data={
                'username': 'admin',
                'password': 'admin123'
            })

            if login_resp.status_code == 302:
                # Get CSRF token
                dashboard = session.get("http://localhost:5000/dashboard")
                soup = BeautifulSoup(dashboard.text, 'html.parser')
                csrf_token = soup.find('meta', {'name': 'csrf-token'})
                if csrf_token:
                    csrf_token = csrf_token.get('content')

                    # Release email
                    release_resp = session.post(
                        f"http://localhost:5000/api/interception/release/{email_id}",
                        json={'target_folder': 'INBOX'},
                        headers={'X-CSRFToken': csrf_token}
                    )

                    if release_resp.status_code == 200:
                        # Verify in inbox
                        from app.utils.crypto import decrypt_credential

                        cursor.execute("""
                            SELECT imap_host, imap_port, imap_username, imap_password
                            FROM email_accounts
                            WHERE email_address = 'ndayijecika@gmail.com'
                        """)

                        account = cursor.fetchone()
                        if account:
                            password = decrypt_credential(account[3])
                            if verify_email_in_inbox(
                                account[0], account[1], account[2],
                                password, original_message_id
                            ):
                                test_results['appears_in_inbox'] = True

        conn.close()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

    # Print results
    print("\n" + "="*80)
    print("TEST RESULTS:")
    print("="*80)

    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:30s} {status}")

    all_passed = all(test_results.values())
    print("\n" + ("🎉 ALL TESTS PASSED!" if all_passed else "⚠️ SOME TESTS FAILED"))

    return all_passed

# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    # Run integration test
    success = integration_test_email_release()
    exit(0 if success else 1)