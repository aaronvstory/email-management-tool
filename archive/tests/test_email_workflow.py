#!/usr/bin/env python3
"""
Complete Email Workflow Test
Tests the entire email interception, modification, and delivery process
"""

import smtplib
import time
import sqlite3
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration
DB_PATH = 'email_manager.db'
API_BASE = 'http://localhost:5000'
SMTP_PROXY_HOST = 'localhost'
SMTP_PROXY_PORT = 8587

def login_to_dashboard():
    """Login to the web dashboard"""
    session = requests.Session()
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    response = session.post(f'{API_BASE}/login', data=login_data)
    return session if response.status_code == 200 else None

def send_test_email():
    """Send a test email through the SMTP proxy"""
    print("\n📧 Sending test email through SMTP proxy...")
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = 'test@sender.com'
    msg['To'] = 'ndayijecika@gmail.com'
    msg['Subject'] = f'Test Email - Interception Test {datetime.now().strftime("%H:%M:%S")}'
    
    body = """This is a test email to verify the interception system.
    
Original content before modification:
- This line should be changed
- Testing timestamp: {timestamp}
- This email should be intercepted and modified

Please intercept and modify this email before delivery!
""".format(timestamp=datetime.now())
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Send through SMTP proxy
        with smtplib.SMTP(SMTP_PROXY_HOST, SMTP_PROXY_PORT) as server:
            server.send_message(msg)
        print("✅ Email sent to SMTP proxy successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def check_pending_emails():
    """Check for pending emails in the database"""
    print("\n🔍 Checking for pending emails...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, sender, recipients, subject, status, created_at
        FROM email_messages
        WHERE status = 'PENDING'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    pending = cursor.fetchall()
    conn.close()
    
    if pending:
        print(f"📬 Found {len(pending)} pending email(s):")
        for email in pending:
            print(f"  - ID: {email['id']}, Subject: {email['subject']}, From: {email['sender']}")
        return pending[0]['id'] if pending else None
    else:
        print("⚠️ No pending emails found")
        return None

def modify_email(email_id):
    """Modify a pending email"""
    print(f"\n✏️ Modifying email ID {email_id}...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get the email
    cursor.execute("SELECT * FROM email_messages WHERE id = ?", (email_id,))
    email = cursor.fetchone()
    
    if email:
        # Modify the email
        new_subject = email['subject'] + " [MODIFIED]"
        new_body = email['body_text'].replace(
            "This line should be changed",
            "✅ This line has been SUCCESSFULLY MODIFIED by the interception system!"
        )
        new_body += "\n\n--- Email modified by Email Management Tool ---"
        
        # Update in database
        cursor.execute("""
            UPDATE email_messages 
            SET subject = ?, body_text = ?, review_notes = ?
            WHERE id = ?
        """, (new_subject, new_body, f"Modified via test at {datetime.now()}", email_id))
        
        conn.commit()
        print(f"✅ Email modified successfully")
        print(f"  - New subject: {new_subject}")
        return True
    
    conn.close()
    return False

def approve_email(email_id):
    """Approve a pending email for sending"""
    print(f"\n✔️ Approving email ID {email_id}...")
    
    session = login_to_dashboard()
    if not session:
        print("❌ Failed to login to dashboard")
        return False
    
    # Approve via API
    response = session.post(f'{API_BASE}/email/{email_id}/action', data={
        'action': 'approve',
        'notes': 'Approved via automated test'
    })
    
    if response.status_code == 200:
        print("✅ Email approved successfully")
        return True
    else:
        print(f"❌ Failed to approve email: {response.status_code}")
        return False

def check_email_status(email_id):
    """Check the final status of an email"""
    print(f"\n📊 Checking final status of email ID {email_id}...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, subject, status, sent_at, approved_by, review_notes
        FROM email_messages
        WHERE id = ?
    """, (email_id,))
    
    email = cursor.fetchone()
    conn.close()
    
    if email:
        print(f"📧 Email Status:")
        print(f"  - Subject: {email['subject']}")
        print(f"  - Status: {email['status']}")
        print(f"  - Sent at: {email['sent_at']}")
        print(f"  - Approved by: {email['approved_by']}")
        print(f"  - Review notes: {email['review_notes']}")
        return email['status']
    return None

def test_inbox_functionality():
    """Test the inbox viewing functionality"""
    print("\n📥 Testing inbox functionality...")
    
    session = login_to_dashboard()
    if not session:
        print("❌ Failed to login")
        return False
    
    response = session.get(f'{API_BASE}/inbox')
    if response.status_code == 200:
        print("✅ Inbox page accessible")
        
        # Check for emails in inbox via database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM email_messages
        """)
        
        count = cursor.fetchone()
        print(f"📬 Total emails in system: {count['count']}")
        conn.close()
        return True
    return False

def test_compose_functionality():
    """Test the compose interface"""
    print("\n✍️ Testing compose functionality...")
    
    session = login_to_dashboard()
    if not session:
        return False
    
    response = session.get(f'{API_BASE}/compose')
    if response.status_code == 200:
        print("✅ Compose page accessible")
        return True
    return False

def run_complete_workflow():
    """Run the complete email workflow test"""
    print("=" * 60)
    print("🚀 COMPLETE EMAIL WORKFLOW TEST")
    print("=" * 60)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: Send email
    print("\n[Step 1/7] Sending test email...")
    results['tests']['send_email'] = send_test_email()
    time.sleep(2)  # Wait for processing
    
    # Test 2: Check for pending email
    print("\n[Step 2/7] Checking for pending emails...")
    email_id = check_pending_emails()
    results['tests']['pending_email_found'] = email_id is not None
    
    if email_id:
        # Test 3: Modify the email
        print("\n[Step 3/7] Modifying the email...")
        results['tests']['modify_email'] = modify_email(email_id)
        
        # Test 4: Approve the email
        print("\n[Step 4/7] Approving the email...")
        results['tests']['approve_email'] = approve_email(email_id)
        time.sleep(2)  # Wait for sending
        
        # Test 5: Check final status
        print("\n[Step 5/7] Checking final status...")
        final_status = check_email_status(email_id)
        results['tests']['email_sent'] = final_status in ['APPROVED', 'SENT']
    
    # Test 6: Check inbox functionality
    print("\n[Step 6/7] Testing inbox functionality...")
    results['tests']['inbox_functional'] = test_inbox_functionality()
    
    # Test 7: Check compose functionality
    print("\n[Step 7/7] Testing compose functionality...")
    results['tests']['compose_functional'] = test_compose_functionality()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results['tests'].values() if v)
    total = len(results['tests'])
    
    for test, result in results['tests'].items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The email management system is fully functional!")
    else:
        print("⚠️ Some tests failed. Please review the results above.")
    
    # Save results
    with open(f'workflow_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return passed == total

if __name__ == "__main__":
    success = run_complete_workflow()
    exit(0 if success else 1)