#!/usr/bin/env python3
"""
Manual Test Email Sender
Sends a real email from Gmail to Hostinger to test IMAP interception
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from datetime import datetime

# Gmail credentials from environment or use test account
GMAIL_ADDRESS = "ndayijecika@gmail.com"
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "")

HOSTINGER_ADDRESS = "mcintyre@corrinbox.com"

def send_test_email():
    """Send test email from Gmail to Hostinger"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"HYBRID IMAP TEST - Gmail→Hostinger {timestamp}"

    # Build message
    msg = MIMEMultipart()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = HOSTINGER_ADDRESS
    msg['Subject'] = subject
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid()

    body = f"""This is a test email to verify the hybrid IMAP strategy is working.

Sent at: {timestamp}
From: {GMAIL_ADDRESS} (Gmail)
To: {HOSTINGER_ADDRESS} (Hostinger)

The IMAP watcher should intercept this email automatically using the hybrid
IDLE+polling strategy with connection health checks and timeout prevention.

Test Components:
- Connection health check before idle_done()
- Graceful IDLE exit with reconnection
- Automatic fallback to polling after 3 IDLE failures
- Recovery mechanism to retry IDLE from polling mode

Expected behavior:
1. Hostinger IMAP watcher detects new email via IDLE
2. Email is intercepted and stored in database (HELD status)
3. Email is moved to Quarantine folder
4. Watcher continues monitoring without timeout issues
"""

    msg.attach(MIMEText(body, 'plain'))

    print(f"\n{'='*70}")
    print("SENDING MANUAL TEST EMAIL")
    print(f"{'='*70}")
    print(f"From: {GMAIL_ADDRESS}")
    print(f"To: {HOSTINGER_ADDRESS}")
    print(f"Subject: {subject}")
    print()

    if not GMAIL_PASSWORD:
        print("❌ ERROR: GMAIL_PASSWORD environment variable not set")
        print("   Set it with: set GMAIL_PASSWORD=your_app_password")
        return False

    try:
        # Connect to Gmail SMTP (port 587 with STARTTLS)
        print("📧 Connecting to Gmail SMTP...")
        smtp = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        print("🔐 Authenticating...")
        smtp.login(GMAIL_ADDRESS, GMAIL_PASSWORD)

        print("📨 Sending email...")
        smtp.send_message(msg)
        smtp.quit()

        print(f"\n✅ EMAIL SENT SUCCESSFULLY!")
        print(f"\n⏳ Now check the database for interception:")
        print(f"   sqlite3 email_manager.db \"SELECT id, subject, status, interception_status, created_at FROM email_messages WHERE subject LIKE '%HYBRID IMAP TEST%' ORDER BY created_at DESC LIMIT 3;\"")
        print()
        return True

    except Exception as e:
        print(f"\n❌ FAILED TO SEND EMAIL: {e}")
        return False

if __name__ == "__main__":
    send_test_email()
