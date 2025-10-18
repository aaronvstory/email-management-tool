#!/usr/bin/env python3
"""
Send Test Email Using Database Credentials
Uses encrypted credentials from email_accounts table
"""
import smtplib
import sqlite3
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from datetime import datetime
from cryptography.fernet import Fernet

DB_PATH = 'email_manager.db'
KEY_PATH = 'key.txt'

def decrypt_credential(encrypted_value):
    """Decrypt credential using Fernet key"""
    if not encrypted_value:
        return None
    try:
        with open(KEY_PATH, 'rb') as f:
            key = f.read()
        cipher = Fernet(key)
        return cipher.decrypt(encrypted_value.encode()).decode()
    except Exception as e:
        print(f"Error decrypting credential: {e}")
        return None

def send_gmail_to_hostinger():
    """Send test email from Gmail to Hostinger using DB credentials"""
    print(f"\n{'='*70}")
    print("HYBRID IMAP TEST - Gmail → Hostinger")
    print(f"{'='*70}\n")

    # Get Gmail account credentials from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    gmail_account = cursor.execute(
        "SELECT * FROM email_accounts WHERE email_address = 'ndayijecika@gmail.com' AND is_active = 1"
    ).fetchone()

    if not gmail_account:
        print("❌ Gmail account not found in database")
        conn.close()
        return False

    # Decrypt SMTP password
    smtp_password = decrypt_credential(gmail_account['smtp_password'])
    if not smtp_password:
        print("❌ Could not decrypt Gmail SMTP password")
        conn.close()
        return False

    conn.close()

    # Build email
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"HYBRID IMAP TEST - {timestamp}"

    msg = MIMEMultipart()
    msg['From'] = gmail_account['email_address']
    msg['To'] = 'mcintyre@corrinbox.com'
    msg['Subject'] = subject
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid()

    body = f"""This is a test email to verify the hybrid IMAP strategy is working.

Sent at: {timestamp}
From: {gmail_account['email_address']} (Gmail)
To: mcintyre@corrinbox.com (Hostinger)

The IMAP watcher should intercept this email automatically using the hybrid
IDLE+polling strategy with connection health checks and timeout prevention.

Hybrid Strategy Features:
✓ Connection health check before idle_done()
✓ Graceful IDLE exit with automatic reconnection
✓ Automatic fallback to polling after 3 IDLE failures
✓ Recovery mechanism to retry IDLE from polling mode every 15 minutes
✓ Timeout prevention with periodic connection validation

Expected behavior:
1. Hostinger IMAP watcher detects new email via IDLE
2. Email is intercepted and stored in database (HELD status)
3. Email is moved to Quarantine folder
4. Watcher continues monitoring without timeout issues
"""

    msg.attach(MIMEText(body, 'plain'))

    print(f"From: {gmail_account['email_address']}")
    print(f"To: mcintyre@corrinbox.com")
    print(f"Subject: {subject}\n")

    try:
        # Connect to Gmail SMTP
        smtp_host = gmail_account['smtp_host']
        smtp_port = int(gmail_account['smtp_port'])
        smtp_username = gmail_account['smtp_username'] or gmail_account['email_address']

        print(f"📧 Connecting to {smtp_host}:{smtp_port}...")

        if smtp_port == 465:
            smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()

        print(f"🔐 Authenticating as {smtp_username}...")
        smtp.login(smtp_username, smtp_password)

        print("📨 Sending email...")
        smtp.send_message(msg)
        smtp.quit()

        print(f"\n{'='*70}")
        print("✅ EMAIL SENT SUCCESSFULLY!")
        print(f"{'='*70}\n")

        print("⏳ Waiting 10 seconds for IMAP interception...")
        import time
        for i in range(10):
            time.sleep(1)
            print(f"   {i+1}/10...", end='\r')

        print("\n\n📊 Checking database for interception...")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute(
            "SELECT id, subject, status, interception_status, created_at FROM email_messages WHERE subject LIKE ? ORDER BY created_at DESC LIMIT 3",
            (f"%HYBRID IMAP TEST%",)
        ).fetchall()

        if rows:
            print("\n✅ INTERCEPTED EMAILS FOUND:\n")
            for row in rows:
                print(f"   ID: {row['id']}")
                print(f"   Subject: {row['subject']}")
                print(f"   Status: {row['status']}")
                print(f"   Interception: {row['interception_status']}")
                print(f"   Created: {row['created_at']}")
                print()
        else:
            print("\n⚠️  No intercepted emails found yet. This may mean:")
            print("   1. IMAP watcher hasn't detected the email yet (wait 30-60s)")
            print("   2. Email went to a different folder (check INBOX directly)")
            print("   3. Watcher credentials need updating")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    send_gmail_to_hostinger()
