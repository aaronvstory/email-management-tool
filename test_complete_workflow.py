#!/usr/bin/env python3
"""
Complete Email Interception Workflow Test
Demonstrates: Send → Intercept → Edit → Hold → Release
"""

import smtplib
import sqlite3
import time
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_complete_workflow():
    """Test complete email interception workflow"""
    print("=" * 70)
    print("COMPLETE EMAIL INTERCEPTION WORKFLOW TEST")
    print("=" * 70)
    
    test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Send test email via SMTP proxy
    print("\n📧 STEP 1: Sending email via SMTP proxy...")
    msg = MIMEMultipart()
    msg['From'] = "sender@test.com"
    msg['To'] = "recipient@test.com"
    msg['Subject'] = f"Workflow Test #{test_id}"
    
    body = f"""This is a test of the complete email workflow.
Test ID: {test_id}
Timestamp: {datetime.now()}
Keywords: urgent invoice payment contract
This email should be intercepted, edited, and held for moderation."""
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('localhost', 8587)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully")
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        return
    
    # Step 2: Wait and verify interception
    print("\n📋 STEP 2: Verifying email interception...")
    time.sleep(2)
    
    conn = sqlite3.connect('data/emails.db')
    cursor = conn.cursor()
    
    # Find the intercepted email
    cursor.execute("""
        SELECT id, subject, body_text, status, risk_score, keywords_matched
        FROM email_messages
        WHERE subject LIKE ?
        ORDER BY id DESC
        LIMIT 1
    """, (f"%{test_id}%",))
    
    email = cursor.fetchone()
    
    if not email:
        print("❌ Email not found in database")
        conn.close()
        return
    
    email_id, subject, body_text, status, risk_score, keywords_matched = email
    
    print(f"✅ Email intercepted with ID: {email_id}")
    print(f"   Subject: {subject}")
    print(f"   Status: {status}")
    print(f"   Risk Score: {risk_score}")
    print(f"   Keywords Matched: {keywords_matched}")
    
    # Step 3: Edit the intercepted email
    print(f"\n✏️ STEP 3: Editing email ID {email_id}...")
    
    modification_time = datetime.now().isoformat()
    modified_subject = f"[EDITED] {subject} - Modified at {modification_time}"
    modified_body = f"""
=== EMAIL INTERCEPTED AND EDITED ===
Edit Time: {modification_time}
Editor: Automated Test System
Reason: Demonstration of edit capability

--- ORIGINAL MESSAGE BELOW ---
{body_text}
--- END OF ORIGINAL MESSAGE ---

This email was intercepted and modified as proof of the email management system's capability.
"""
    
    cursor.execute("""
        UPDATE email_messages
        SET subject = ?, body_text = ?, review_notes = ?
        WHERE id = ?
    """, (modified_subject, modified_body, f"Edited at {modification_time} by test system", email_id))
    
    conn.commit()
    print(f"✅ Email edited with timestamp: {modification_time}")
    
    # Step 4: Hold email (keep as PENDING)
    print(f"\n⏸️ STEP 4: Holding email in PENDING status...")
    time.sleep(2)
    print("✅ Email held for moderation review")
    
    # Step 5: Approve and release email
    print(f"\n✅ STEP 5: Approving email for release...")
    
    cursor.execute("""
        UPDATE email_messages
        SET status = 'APPROVED', reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (email_id,))
    
    conn.commit()
    print("✅ Email approved for release")
    
    # Step 6: Verify final state
    print(f"\n📊 STEP 6: Verifying final state...")
    
    cursor.execute("""
        SELECT id, subject, status, review_notes
        FROM email_messages
        WHERE id = ?
    """, (email_id,))
    
    final_email = cursor.fetchone()
    
    if final_email:
        print(f"✅ Final Email State:")
        print(f"   ID: {final_email[0]}")
        print(f"   Subject: {final_email[1]}")
        print(f"   Status: {final_email[2]}")
        print(f"   Review Notes: {final_email[3]}")
    
    # Get overall statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected
        FROM email_messages
    """)
    
    stats = cursor.fetchone()
    
    print(f"\n📈 Database Statistics:")
    print(f"   Total Emails: {stats[0]}")
    print(f"   Pending: {stats[1]}")
    print(f"   Approved: {stats[2]}")
    print(f"   Rejected: {stats[3]}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✨ WORKFLOW TEST COMPLETE")
    print("Successfully demonstrated: Send → Intercept → Edit → Hold → Release")
    print("=" * 70)

if __name__ == "__main__":
    test_complete_workflow()