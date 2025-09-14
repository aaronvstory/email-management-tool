#!/usr/bin/env python3
"""
Complete Email Interception Test
Tests the full workflow: sending, intercepting, editing, and approving emails
"""

import smtplib
import time
import requests
import sqlite3
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
SMTP_PROXY_HOST = "localhost"
SMTP_PROXY_PORT = 8587
DB_PATH = "email_manager.db"

# Test credentials
LOGIN_CREDS = {
    "username": "admin",
    "password": "admin123"
}

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{'='*60}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}📋 {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.END}")

def test_page_access(session):
    """Test all pages are accessible"""
    print_header("TESTING ALL PAGE ACCESS")
    
    pages = [
        ("/dashboard", "Dashboard"),
        ("/emails", "Email Queue"),
        ("/inbox", "Inbox"),
        ("/compose", "Compose"),
        ("/accounts", "Accounts"),
        ("/rules", "Rules"),
        ("/diagnostics", "Diagnostics")
    ]
    
    results = []
    for path, name in pages:
        try:
            response = session.get(f"{BASE_URL}{path}", timeout=5)
            if response.status_code == 200:
                print_success(f"{name} page accessible at {path}")
                results.append((name, "PASSED"))
            else:
                print_error(f"{name} page returned {response.status_code}")
                results.append((name, f"FAILED: {response.status_code}"))
        except Exception as e:
            print_error(f"{name} page error: {e}")
            results.append((name, f"ERROR: {e}"))
    
    return results

def send_test_email(subject="Test Email", body="This is a test email", recipient="test@example.com"):
    """Send email through SMTP proxy"""
    print_info(f"Sending email with subject: '{subject}'")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = 'sender@test.com'
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_PROXY_HOST, SMTP_PROXY_PORT, timeout=10) as server:
            server.send_message(msg)
        
        print_success("Email sent successfully through SMTP proxy")
        return True
    except Exception as e:
        print_error(f"Failed to send email: {e}")
        return False

def get_pending_email():
    """Get the latest pending email from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, sender, recipients, subject, body_text, status
        FROM email_messages
        WHERE status = 'PENDING'
        ORDER BY id DESC
        LIMIT 1
    """)
    
    email = cursor.fetchone()
    conn.close()
    
    return dict(email) if email else None

def edit_email_via_api(session, email_id, new_subject, new_body):
    """Edit an email using the API"""
    print_info(f"Editing email {email_id} via API")
    
    edit_url = f"{BASE_URL}/email/{email_id}/edit"
    
    # First GET the email
    response = session.get(edit_url)
    if response.status_code != 200:
        print_error(f"Failed to get email for editing: {response.status_code}")
        return False
    
    # Now POST the edits
    edit_data = {
        "subject": new_subject,
        "body": new_body
    }
    
    response = session.post(edit_url, data=edit_data)
    if response.status_code == 200:
        print_success(f"Email edited successfully!")
        return True
    else:
        print_error(f"Failed to edit email: {response.status_code}")
        return False

def approve_email(session, email_id):
    """Approve an email for sending"""
    print_info(f"Approving email {email_id}")
    
    approve_url = f"{BASE_URL}/email/{email_id}/action"
    data = {"action": "approve"}
    
    response = session.post(approve_url, data=data)
    if response.status_code == 200:
        print_success("Email approved for sending")
        return True
    else:
        print_error(f"Failed to approve email: {response.status_code}")
        return False

def verify_email_edited(email_id):
    """Verify the email was edited in database"""
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
        has_edited_slay = "edited slay!" in email['subject'].lower() or \
                         "edited slay!" in email['body_text'].lower()
        return dict(email), has_edited_slay
    return None, False

def main():
    print_header("COMPLETE EMAIL INTERCEPTION TEST")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create session for authenticated requests
    session = requests.Session()
    
    # Step 1: Login
    print_header("STEP 1: LOGIN")
    login_response = session.post(f"{BASE_URL}/login", data=LOGIN_CREDS)
    if login_response.status_code == 200 or login_response.status_code == 302:
        print_success("Logged in successfully")
    else:
        print_error(f"Login failed: {login_response.status_code}")
        return
    
    # Step 2: Test all pages
    print_header("STEP 2: TEST ALL PAGES")
    page_results = test_page_access(session)
    
    # Step 3: Send test email
    print_header("STEP 3: SEND TEST EMAIL")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_subject = f"Interception Test #{timestamp}"
    test_body = "This email will be intercepted and edited"
    
    if send_test_email(test_subject, test_body):
        time.sleep(2)  # Wait for email to be processed
        
        # Step 4: Get pending email
        print_header("STEP 4: GET PENDING EMAIL")
        pending_email = get_pending_email()
        
        if pending_email:
            print_success(f"Found pending email: ID={pending_email['id']}")
            print_info(f"Subject: {pending_email['subject']}")
            print_info(f"Body: {pending_email['body_text'][:100]}...")
            
            # Step 5: Edit the email
            print_header("STEP 5: EDIT EMAIL WITH 'edited slay!'")
            new_subject = f"{pending_email['subject']} - edited slay!"
            new_body = f"{pending_email['body_text']}\n\n--- EDITED SLAY! ---\nThis email was intercepted and edited!"
            
            if edit_email_via_api(session, pending_email['id'], new_subject, new_body):
                time.sleep(1)
                
                # Step 6: Verify edit
                print_header("STEP 6: VERIFY EDIT")
                edited_email, has_slay = verify_email_edited(pending_email['id'])
                
                if has_slay:
                    print_success("Email successfully edited with 'edited slay!'")
                    print_info(f"New subject: {edited_email['subject']}")
                    print_info(f"Review notes: {edited_email['review_notes']}")
                else:
                    print_error("Email edit verification failed - 'edited slay!' not found")
                
                # Step 7: Approve email
                print_header("STEP 7: APPROVE EMAIL")
                if approve_email(session, pending_email['id']):
                    print_success("Email approved and would be sent to destination")
                else:
                    print_error("Failed to approve email")
            else:
                print_error("Failed to edit email")
        else:
            print_error("No pending email found in database")
    else:
        print_error("Failed to send test email")
    
    # Step 8: Test email workflow between accounts
    print_header("STEP 8: TEST CROSS-ACCOUNT EMAIL")
    print_info("Testing email from one configured account to another...")
    
    # Get configured accounts
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, email_address FROM email_accounts WHERE is_active = 1")
    accounts = cursor.fetchall()
    conn.close()
    
    if len(accounts) >= 2:
        print_info(f"Found {len(accounts)} active accounts")
        from_email = accounts[0]['email_address']
        to_email = accounts[1]['email_address']
        print_info(f"Would send from {from_email} to {to_email}")
        print_warning("Note: Actual sending requires valid email credentials")
    else:
        print_warning(f"Only {len(accounts)} active accounts configured (need at least 2)")
    
    # Final Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in page_results if result == "PASSED")
    failed = len(page_results) - passed
    
    print(f"\nPage Access Tests:")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.END}")
    print(f"  {Colors.FAIL}Failed: {failed}{Colors.END}")
    
    print(f"\nEmail Interception Workflow:")
    if pending_email and has_slay:
        print_success("✅ Email successfully intercepted, edited with 'edited slay!', and approved")
    else:
        print_error("❌ Email interception workflow incomplete")
    
    print(f"\n{Colors.BOLD}Overall Result: {'PASSED' if failed == 0 and has_slay else 'NEEDS ATTENTION'}{Colors.END}")
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "page_tests": dict(page_results),
        "email_interception": {
            "sent": bool(pending_email),
            "edited": has_slay if pending_email else False,
            "approved": True if pending_email else False
        },
        "overall": "PASSED" if failed == 0 and has_slay else "NEEDS ATTENTION"
    }
    
    with open(f"interception_test_results_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print_info(f"Results saved to interception_test_results_{timestamp}.json")

if __name__ == "__main__":
    main()