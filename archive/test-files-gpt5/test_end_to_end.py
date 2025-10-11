#!/usr/bin/env python3
"""End-to-end email delivery test"""

import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_send_via_proxy():
    """Send test email through SMTP proxy"""
    print("=" * 80)
    print("END-TO-END EMAIL DELIVERY TEST")
    print("=" * 80)
    print()

    # Test email details
    sender = "test@example.com"
    recipient = "mcintyre@corrinbox.com"
    subject = f"E2E Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    body = "This is an end-to-end test email sent through the SMTP proxy."

    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    print(f"1. Sending test email:")
    print(f"   From: {sender}")
    print(f"   To: {recipient}")
    print(f"   Subject: {subject}")
    print()

    # Send via SMTP proxy
    try:
        print("2. Connecting to SMTP proxy on localhost:8587...")
        server = smtplib.SMTP('localhost', 8587)
        server.set_debuglevel(0)  # Set to 1 for debug output

        print("3. Sending email...")
        result = server.send_message(msg)
        server.quit()

        print("   ✅ Email sent successfully to proxy!")
        print()

        # Check database for the email
        print("4. Checking database for intercepted email...")
        time.sleep(2)  # Give it time to process

        import sqlite3
        conn = sqlite3.connect('email_manager.db')
        cursor = conn.cursor()

        # Look for our test email
        cursor.execute("""
            SELECT id, subject, sender, recipients, status, interception_status,
                   risk_score, created_at
            FROM email_messages
            WHERE subject = ?
            ORDER BY id DESC
            LIMIT 1
        """, (subject,))

        result = cursor.fetchone()

        if result:
            print("   ✅ Email found in database!")
            print(f"      ID: {result[0]}")
            print(f"      Subject: {result[1]}")
            print(f"      Sender: {result[2]}")
            print(f"      Recipients: {result[3]}")
            print(f"      Status: {result[4]}")
            print(f"      Interception: {result[5]}")
            print(f"      Risk Score: {result[6]}")
            print(f"      Created: {result[7]}")

            # Now test releasing it
            email_id = result[0]
            print()
            print(f"5. Testing release of email ID {email_id}...")

            # We need to do this via the API with proper auth
            import requests
            from bs4 import BeautifulSoup

            session = requests.Session()

            # Login
            login_page = session.get("http://localhost:5000/")
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_token = None
            meta_tag = soup.find('meta', {'name': 'csrf-token'})
            if meta_tag:
                csrf_token = meta_tag.get('content')

            login_data = {
                'username': 'admin',
                'password': 'admin123',
                'csrf_token': csrf_token
            }

            login_response = session.post("http://localhost:5000/login", data=login_data, allow_redirects=False)

            if login_response.status_code == 302:
                # Get fresh CSRF token
                dashboard = session.get("http://localhost:5000/dashboard")
                soup = BeautifulSoup(dashboard.text, 'html.parser')
                meta_tag = soup.find('meta', {'name': 'csrf-token'})
                if meta_tag:
                    csrf_token = meta_tag.get('content')

                # Try to release the email
                release_response = session.post(
                    f"http://localhost:5000/api/interception/release/{email_id}",
                    headers={'X-CSRFToken': csrf_token} if csrf_token else {}
                )

                print(f"   Release response: {release_response.status_code}")
                if release_response.status_code == 200:
                    print("   ✅ Email released successfully!")

                    # Check final status
                    cursor.execute("""
                        SELECT status, interception_status
                        FROM email_messages
                        WHERE id = ?
                    """, (email_id,))

                    final_status = cursor.fetchone()
                    if final_status:
                        print(f"   Final status: {final_status[0]}, Interception: {final_status[1]}")
                else:
                    print(f"   ❌ Release failed: {release_response.text[:100]}")
            else:
                print("   ❌ Failed to authenticate for release test")

        else:
            print("   ❌ Email not found in database!")
            print("   Checking recent emails...")

            cursor.execute("""
                SELECT id, subject, created_at
                FROM email_messages
                ORDER BY id DESC
                LIMIT 5
            """)

            recent = cursor.fetchall()
            if recent:
                print("   Recent emails in database:")
                for r in recent:
                    print(f"      ID {r[0]}: {r[1]} ({r[2]})")

        conn.close()

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_send_via_proxy()