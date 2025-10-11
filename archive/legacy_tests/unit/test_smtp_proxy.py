#!/usr/bin/env python3
"""
Direct SMTP Proxy Test
"""

import smtplib
import sqlite3
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_smtp_proxy():
    """Test SMTP proxy directly"""
    print("Testing SMTP Proxy on localhost:8587")
    print("-" * 50)
    
    # Create test message
    msg = MIMEMultipart()
    msg['From'] = "test@example.com"
    msg['To'] = "recipient@example.com"
    msg['Subject'] = f"Direct SMTP Test - {datetime.now().strftime('%H:%M:%S')}"
    
    body = f"""This is a direct test of the SMTP proxy.
Timestamp: {datetime.now()}
Keywords: invoice payment urgent
This should be intercepted and stored in the database.
"""
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Connect to proxy
        print("Connecting to SMTP proxy...")
        server = smtplib.SMTP('localhost', 8587)
        server.set_debuglevel(1)  # Enable debug output
        
        # Send message
        print("Sending test email...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent successfully")
        
        # Wait for processing
        print("Waiting 2 seconds for processing...")
        time.sleep(2)
        
        # Check database
        print("\nChecking database...")
        conn = sqlite3.connect('data/emails.db')
        cursor = conn.cursor()
        
        # Get recent emails
        cursor.execute("""
            SELECT id, subject, sender, status, risk_score, created_at
            FROM email_messages
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        emails = cursor.fetchall()
        
        if emails:
            print(f"\nFound {len(emails)} recent emails:")
            for email in emails:
                print(f"  ID: {email[0]}")
                print(f"  Subject: {email[1]}")
                print(f"  From: {email[2]}")
                print(f"  Status: {email[3]}")
                print(f"  Risk Score: {email[4]}")
                print(f"  Created: {email[5]}")
                print("-" * 30)
        else:
            print("❌ No emails found in database")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_smtp_proxy()