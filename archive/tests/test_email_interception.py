#!/usr/bin/env python3
"""
Test Email Interception and Editing
"""

import smtplib
import time
import sqlite3
from email.mime.text import MIMEText
from datetime import datetime

# Configuration
SMTP_HOST = "localhost"
SMTP_PORT = 8587
DB_PATH = "email_manager.db"

def send_test_email():
    """Send a test email through the SMTP proxy"""
    print("\n📧 STEP 1: Sending test email through SMTP proxy...")
    
    msg = MIMEText("This is a test email that will be intercepted and edited.")
    msg['Subject'] = f"Test Email {datetime.now().strftime('%H:%M:%S')}"
    msg['From'] = 'test@sender.com'
    msg['To'] = 'test@recipient.com'
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.send_message(msg)
        print("✅ Email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        return False

def get_pending_email():
    """Get the latest pending email"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, sender, subject, body_text, status 
        FROM email_messages 
        WHERE status = 'PENDING' 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    email = cursor.fetchone()
    conn.close()
    
    if email:
        return dict(email)
    return None

def edit_email(email_id, new_text):
    """Edit the email directly in database"""
    print(f"\n✏️ STEP 3: Editing email {email_id} with 'edited slay!'...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update the email
    cursor.execute("""
        UPDATE email_messages 
        SET subject = subject || ' - edited slay!',
            body_text = body_text || '\n\n--- EDITED SLAY! ---\nThis email was intercepted and modified!',
            review_notes = 'Email edited via test script at ' || datetime('now')
        WHERE id = ?
    """, (email_id,))
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    if rows_affected > 0:
        print("✅ Email edited successfully!")
        return True
    else:
        print("❌ Failed to edit email")
        return False

def verify_edit(email_id):
    """Verify the email was edited"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT subject, body_text, review_notes 
        FROM email_messages 
        WHERE id = ?
    """, (email_id,))
    
    email = cursor.fetchone()
    conn.close()
    
    if email:
        if "edited slay!" in email['subject'] and "EDITED SLAY!" in email['body_text']:
            print("✅ Email contains 'edited slay!' - verification successful!")
            print(f"   Subject: {email['subject']}")
            print(f"   Review notes: {email['review_notes']}")
            return True
        else:
            print("❌ Email does not contain 'edited slay!'")
            return False
    return False

def approve_email(email_id):
    """Approve the email for sending"""
    print(f"\n📤 STEP 5: Approving email {email_id} for sending...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE email_messages 
        SET status = 'APPROVED'
        WHERE id = ?
    """, (email_id,))
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    if rows_affected > 0:
        print("✅ Email approved for sending!")
        return True
    else:
        print("❌ Failed to approve email")
        return False

def main():
    print("="*60)
    print("EMAIL INTERCEPTION AND EDITING TEST")
    print("="*60)
    
    # Send test email
    if send_test_email():
        time.sleep(2)  # Wait for processing
        
        # Get the pending email
        print("\n📋 STEP 2: Checking for intercepted email...")
        email = get_pending_email()
        
        if email:
            print(f"✅ Found pending email:")
            print(f"   ID: {email['id']}")
            print(f"   From: {email['sender']}")
            print(f"   Subject: {email['subject']}")
            print(f"   Status: {email['status']}")
            
            # Edit the email
            if edit_email(email['id'], "edited slay!"):
                time.sleep(1)
                
                # Verify the edit
                print("\n🔍 STEP 4: Verifying edit...")
                if verify_edit(email['id']):
                    
                    # Approve the email
                    if approve_email(email['id']):
                        print("\n"+"="*60)
                        print("🎉 SUCCESS! Email workflow complete:")
                        print("1. ✅ Email sent through SMTP proxy")
                        print("2. ✅ Email intercepted and held as PENDING")
                        print("3. ✅ Email edited with 'edited slay!'")
                        print("4. ✅ Edit verified in database")
                        print("5. ✅ Email approved for sending")
                        print("="*60)
                        return True
        else:
            print("❌ No pending email found - interception may have failed")
    
    print("\n❌ Test failed - email interception not working properly")
    return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)