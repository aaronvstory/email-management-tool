#!/usr/bin/env python3
"""Send a test email to trigger IMAP interception"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

def send_test_email():
    """Send test email to one of our monitored accounts"""

    # Gmail account credentials (sender)
    sender_email = "ndayijecika@gmail.com"
    sender_password = "bjormgplhgwkgpad"  # App password

    # Send to the same account (so we can intercept it)
    recipient_email = "ndayijecika@gmail.com"

    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Test Email - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Add body
    body = f"""
    This is a test email sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Keywords that should trigger rules:
    - urgent
    - invoice
    - payment

    This email should be intercepted by IMAP monitoring and stored in the database.
    """

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to Gmail SMTP
        print("Connecting to Gmail SMTP...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send email
        print(f"Sending test email to {recipient_email}...")
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()

        print(f"✅ Test email sent successfully!")
        print(f"   Subject: {msg['Subject']}")
        print(f"   To: {recipient_email}")
        print("\nEmail should appear in the inbox within a few seconds.")
        print("Check the database to verify it was stored with account_id.")

    except Exception as e:
        print(f"❌ Failed to send test email: {e}")

if __name__ == "__main__":
    send_test_email()