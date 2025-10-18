"""
Send test email from Gmail to Hostinger for automatic interception test
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Gmail (sender) credentials from .env
GMAIL_EMAIL = os.getenv('GMAIL_ADDRESS', 'ndayijecika@gmail.com')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD', '')

# Hostinger (receiver)
HOSTINGER_EMAIL = 'mcintyre@corrinbox.com'

# SMTP settings for Gmail
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587  # STARTTLS

def send_test_email():
    """Send test email from Gmail to Hostinger"""
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Create message
    msg = MIMEMultipart()
    msg['From'] = GMAIL_EMAIL
    msg['To'] = HOSTINGER_EMAIL
    msg['Subject'] = f'INVOICE - Test Gmail→Hostinger {timestamp}'

    body = f"""This is a test email for automatic interception validation.

Sent from: Gmail (ndayijecika@gmail.com)
Sent to: Hostinger (mcintyre@corrinbox.com)
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This email should be automatically intercepted at Hostinger's INBOX by the polling watcher.

Test flow:
1. Gmail sends → Hostinger receives
2. Email automatically intercepted (HELD status)
3. Verify in database and UI

--- ORIGINAL BODY (before potential edit) ---
"""

    msg.attach(MIMEText(body, 'plain'))

    print(f"📧 Sending test email from {GMAIL_EMAIL} to {HOSTINGER_EMAIL}...")
    print(f"   Subject: {msg['Subject']}")

    try:
        # Connect with STARTTLS (port 587)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
            server.send_message(msg)
            print(f"✅ Test email sent successfully at {timestamp}!")
            print(f"   Subject: {msg['Subject']}")
            return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

if __name__ == "__main__":
    if not GMAIL_PASSWORD:
        print("❌ Error: GMAIL_PASSWORD not set in .env file")
        exit(1)

    success = send_test_email()
    exit(0 if success else 1)
