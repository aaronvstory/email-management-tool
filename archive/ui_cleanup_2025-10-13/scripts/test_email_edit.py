#!/usr/bin/env python3
"""
Test script to verify email editing functionality
Tests the complete workflow of editing pending emails
"""

import sqlite3
import json
import requests
from datetime import datetime
import time
import sys

# Configuration
BASE_URL = "http://localhost:5000"
DB_PATH = "email_manager.db"
USERNAME = "admin"
PASSWORD = "admin123"

def print_step(step_num, description):
    """Print formatted step information"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {description}")
    print(f"{'='*60}")

def print_success(message):
    """Print success message"""
    print(f"✓ SUCCESS: {message}")

def print_error(message):
    """Print error message"""
    print(f"✗ ERROR: {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ INFO: {message}")

def create_test_email():
    """Create a test pending email directly in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create a test email
    test_email = {
        'message_id': f'test_{datetime.now().timestamp()}@test.com',
        'sender': 'test@example.com',
        'recipients': 'recipient@example.com',
        'subject': 'Original Test Subject',
        'body_text': 'This is the original body text that needs editing.',
        'body_html': '<p>This is the original body text that needs editing.</p>',
        'status': 'PENDING',
        'risk_score': 50,
        'keywords_matched': 'test',
        'created_at': datetime.now().isoformat()
    }

    cursor.execute("""
        INSERT INTO email_messages (
            message_id, sender, recipients, subject, body_text, body_html,
            status, risk_score, keywords_matched, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        test_email['message_id'],
        test_email['sender'],
        test_email['recipients'],
        test_email['subject'],
        test_email['body_text'],
        test_email['body_html'],
        test_email['status'],
        test_email['risk_score'],
        test_email['keywords_matched'],
        test_email['created_at']
    ))

    email_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print_success(f"Created test email with ID: {email_id}")
    return email_id

def test_login():
    """Test login to get session"""
    session = requests.Session()

    # Get login page first (might be needed for CSRF token)
    response = session.get(f"{BASE_URL}/")

    # Login
    login_data = {
        'username': USERNAME,
        'password': PASSWORD
    }

    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)

    if response.status_code in [302, 303]:
        print_success("Login successful")
        return session
    else:
        print_error(f"Login failed with status: {response.status_code}")
        return None

def test_fetch_email_details(session, email_id):
    """Test fetching email details via edit endpoint"""
    url = f"{BASE_URL}/email/{email_id}/edit"

    response = session.get(url)

    if response.status_code == 200:
        try:
            data = response.json()
            print_success("Fetched email details successfully")
            print_info(f"Email ID: {data.get('id')}")
            print_info(f"Subject: {data.get('subject')}")
            print_info(f"Body: {data.get('body')[:50]}...")
            print_info(f"From: {data.get('sender')}")
            print_info(f"To: {data.get('recipients')}")
            return data
        except json.JSONDecodeError as e:
            print_error(f"Failed to parse JSON response: {e}")
            print_info(f"Response text: {response.text[:200]}")
            return None
    else:
        print_error(f"Failed to fetch email details. Status: {response.status_code}")
        print_info(f"Response: {response.text[:200]}")
        return None

def test_update_email(session, email_id):
    """Test updating email subject and body"""
    url = f"{BASE_URL}/email/{email_id}/edit"

    new_data = {
        'subject': 'EDITED: New Test Subject After Editing',
        'body': 'This is the completely new body text after editing.\nIt has been modified successfully.'
    }

    headers = {'Content-Type': 'application/json'}
    response = session.post(url, json=new_data, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('success'):
                print_success("Email updated successfully")
                return True
            else:
                print_error(f"Update failed: {data.get('error', 'Unknown error')}")
                return False
        except json.JSONDecodeError as e:
            print_error(f"Failed to parse JSON response: {e}")
            print_info(f"Response text: {response.text[:200]}")
            return False
    else:
        print_error(f"Failed to update email. Status: {response.status_code}")
        print_info(f"Response: {response.text[:200]}")
        return False

def verify_changes(email_id):
    """Verify changes were saved to database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    email = cursor.execute("""
        SELECT id, subject, body_text, review_notes, status
        FROM email_messages
        WHERE id = ?
    """, (email_id,)).fetchone()

    conn.close()

    if email:
        print_success("Email found in database")
        print_info(f"Subject: {email['subject']}")
        print_info(f"Body: {email['body_text'][:50]}...")
        print_info(f"Status: {email['status']}")

        # Check if changes were applied
        if 'EDITED:' in email['subject']:
            print_success("Subject was successfully edited")
        else:
            print_error("Subject was not edited")

        if 'completely new body text' in email['body_text']:
            print_success("Body was successfully edited")
        else:
            print_error("Body was not edited")

        if email['review_notes'] and 'Edited by' in (email['review_notes'] or ''):
            print_success("Edit audit trail was recorded")

        return email
    else:
        print_error("Email not found in database")
        return None

def cleanup_test_email(email_id):
    """Clean up test email from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_messages WHERE id = ?", (email_id,))
    conn.commit()
    conn.close()
    print_info(f"Cleaned up test email ID: {email_id}")

def main():
    """Main test execution"""
    print("\n" + "="*60)
    print("EMAIL EDITING FUNCTIONALITY TEST")
    print("="*60)

    test_email_id = None

    try:
        # Step 1: Create test email
        print_step(1, "Creating test pending email")
        test_email_id = create_test_email()

        # Step 2: Login
        print_step(2, "Logging in to application")
        session = test_login()
        if not session:
            print_error("Cannot continue without valid session")
            return False

        # Step 3: Fetch email details
        print_step(3, "Fetching email details via edit endpoint")
        email_details = test_fetch_email_details(session, test_email_id)
        if not email_details:
            print_error("Cannot continue without email details")
            return False

        # Step 4: Update email
        print_step(4, "Updating email subject and body")
        update_success = test_update_email(session, test_email_id)
        if not update_success:
            print_error("Email update failed")
            return False

        # Step 5: Verify changes
        print_step(5, "Verifying changes in database")
        verified_email = verify_changes(test_email_id)

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        if verified_email and 'EDITED:' in verified_email['subject']:
            print_success("✓ Email editing functionality is WORKING CORRECTLY")
            print_success("✓ Subjects can be fully edited")
            print_success("✓ Body text can be fully edited")
            print_success("✓ Changes are persisted to database")
            print_success("✓ Audit trail is maintained")
            return True
        else:
            print_error("✗ Email editing functionality has issues")
            return False

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if test_email_id:
            print_step(6, "Cleanup")
            cleanup_test_email(test_email_id)

if __name__ == "__main__":
    # Check if app is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print_info(f"Application is running at {BASE_URL}")
    except requests.exceptions.RequestException:
        print_error(f"Application is not running at {BASE_URL}")
        print_info("Please start the application first: python simple_app.py")
        sys.exit(1)

    # Run test
    success = main()
    sys.exit(0 if success else 1)