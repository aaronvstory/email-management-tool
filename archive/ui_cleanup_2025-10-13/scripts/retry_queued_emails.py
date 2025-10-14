#!/usr/bin/env python
"""
Retry sending queued emails when SMTP becomes available
Can be run manually or scheduled as a task
"""

import sqlite3
import smtplib
import ssl
import socket
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from cryptography.fernet import Fernet

# Database path
DB_PATH = 'email_manager.db'

# Load encryption key
try:
    with open('key.txt', 'r') as f:
        key = f.read().strip()
        cipher_suite = Fernet(key.encode() if isinstance(key, str) else key)
except FileNotFoundError:
    print("Error: key.txt file not found")
    exit(1)

def decrypt_credential(encrypted_text):
    """Decrypt a credential"""
    if not encrypted_text:
        return None
    try:
        return cipher_suite.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def test_smtp_connectivity(host, port):
    """Quick test to see if SMTP port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def send_queued_email(email, account):
    """Attempt to send a queued email"""
    try:
        # Decrypt password
        smtp_password = decrypt_credential(account['smtp_password'])
        if not smtp_password:
            return False, "Failed to decrypt password"

        # Remove spaces for Gmail app passwords
        if 'gmail' in account['smtp_host'].lower():
            smtp_password = smtp_password.replace(' ', '')

        smtp_host = account['smtp_host']
        smtp_port = int(account['smtp_port']) if account['smtp_port'] else 587

        # Test connectivity first
        if not test_smtp_connectivity(smtp_host, smtp_port):
            return False, f"SMTP port {smtp_port} still blocked"

        # Create message
        msg = MIMEMultipart()
        msg['From'] = email['sender']
        recipients = json.loads(email['recipients'])
        msg['To'] = recipients[0] if recipients else ''
        msg['Subject'] = email['subject']
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = email['message_id'] or make_msgid()

        # Add body
        msg.attach(MIMEText(email['body_text'], 'plain'))

        # Connect and send
        context = ssl.create_default_context()

        if smtp_port == 465 or account['smtp_use_ssl']:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30, context=context)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

        server.login(account['smtp_username'], smtp_password)
        server.send_message(msg)
        server.quit()

        return True, "Email sent successfully"

    except Exception as e:
        return False, str(e)

def main():
    print("="*60)
    print("Retry Queued Emails")
    print("="*60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all queued emails
    queued_emails = cursor.execute("""
        SELECT * FROM email_messages
        WHERE status = 'QUEUED'
        ORDER BY created_at ASC
    """).fetchall()

    if not queued_emails:
        print("\n✅ No queued emails to process")
        conn.close()
        return

    print(f"\nFound {len(queued_emails)} queued email(s)")

    # Process each queued email
    sent_count = 0
    failed_count = 0

    for email in queued_emails:
        print(f"\n{'='*40}")
        print(f"Processing: {email['subject']}")
        print(f"To: {email['recipients']}")

        # Get the account for this email
        if email['account_id']:
            account = cursor.execute("""
                SELECT * FROM email_accounts
                WHERE id = ?
            """, (email['account_id'],)).fetchone()
        else:
            # Try to find account by sender email
            account = cursor.execute("""
                SELECT * FROM email_accounts
                WHERE email_address = ?
            """, (email['sender'],)).fetchone()

        if not account:
            print("❌ No account found for this email")
            failed_count += 1
            continue

        print(f"Using account: {account['account_name']}")

        # Try to send
        success, message = send_queued_email(email, account)

        if success:
            print(f"✅ {message}")
            # Update status to SENT
            cursor.execute("""
                UPDATE email_messages
                SET status = 'SENT', sent_at = CURRENT_TIMESTAMP,
                    review_notes = review_notes || ' | Sent via retry script'
                WHERE id = ?
            """, (email['id'],))
            conn.commit()
            sent_count += 1
        else:
            print(f"❌ {message}")
            # Update review notes with failure reason
            cursor.execute("""
                UPDATE email_messages
                SET review_notes = review_notes || ? || CURRENT_TIMESTAMP
                WHERE id = ?
            """, (f" | Retry failed: {message[:100]} at ", email['id']))
            conn.commit()
            failed_count += 1

    conn.close()

    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    print(f"✅ Sent: {sent_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📬 Still queued: {failed_count}")

    if failed_count > 0:
        print("\n💡 Emails still cannot be sent because:")
        print("   • SMTP ports are still blocked")
        print("   • Try disconnecting from VPN")
        print("   • Or wait until network allows SMTP")

if __name__ == "__main__":
    main()