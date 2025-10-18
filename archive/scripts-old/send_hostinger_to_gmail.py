"""
Send test email from Hostinger to Gmail for reverse interception test
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Hostinger (sender) credentials from .env
HOSTINGER_EMAIL = os.getenv('HOSTINGER_ADDRESS', 'mcintyre@corrinbox.com')
HOSTINGER_PASSWORD = os.getenv('HOSTINGER_PASSWORD', '')

# Gmail (receiver)
GMAIL_EMAIL = 'ndayijecika@gmail.com'

# SMTP settings for Hostinger
SMTP_HOST = 'smtp.hostinger.com'
SMTP_PORT = 465  # SSL

def send_test_email():
    """Send test email from Hostinger to Gmail"""
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Create message
    msg = MIMEMultipart()
    msg['From'] = HOSTINGER_EMAIL
    msg['To'] = GMAIL_EMAIL
    msg['Subject'] = f'INVOICE - Reverse Test Hostinger→Gmail {timestamp}'

    body = f"""This is a REVERSE test email for the complete edit/release flow.

Sent from: Hostinger (mcintyre@corrinbox.com)
Sent to: Gmail (ndayijecika@gmail.com)
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This email should be intercepted at Gmail's INBOX.
After editing with timestamp, only the edited version should appear in Gmail's web interface.

Test flow:
1. Hostinger sends → Gmail receives
2. Email intercepted (HELD status)
3. Edit body with timestamp
4. Release to Gmail INBOX
5. Verify Gmail web shows ONLY edited version (no duplicate)

--- ORIGINAL BODY (before edit) ---
"""

    msg.attach(MIMEText(body, 'plain'))

    print(f"📧 Sending test email from {HOSTINGER_EMAIL} to {GMAIL_EMAIL}...")
    print(f"   Subject: {msg['Subject']}")

    try:
        # Connect with SSL (port 465)
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(HOSTINGER_EMAIL, HOSTINGER_PASSWORD)
            server.send_message(msg)
            print(f"✅ Test email sent successfully at {timestamp}!")
            print(f"   Subject: {msg['Subject']}")
            return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

if __name__ == "__main__":
    if not HOSTINGER_PASSWORD:
        print("❌ Error: HOSTINGER_PASSWORD not set in .env file")
        exit(1)

    success = send_test_email()
    exit(0 if success else 1)
