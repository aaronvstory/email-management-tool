#!/usr/bin/env python3
"""Test email edit persistence - Final validation after GPT-5 fixes"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import json

BASE_URL = "http://localhost:5000"
DB_PATH = "email_manager.db"

def test_edit_persistence():
    """Test that email edit saves both subject AND body_text"""

    print("=" * 80)
    print("EMAIL EDIT PERSISTENCE TEST")
    print("=" * 80)
    print()

    # Create session
    session = requests.Session()

    # Step 1: Login
    print("1. Logging in...")
    login_page = session.get(f"{BASE_URL}/")
    soup = BeautifulSoup(login_page.text, 'html.parser')

    csrf_token = None
    # Try meta tag first
    meta_tag = soup.find('meta', {'name': 'csrf-token'})
    if meta_tag:
        csrf_token = meta_tag.get('content')

    # Fall back to form field
    if not csrf_token:
        form_token = soup.find('input', {'name': 'csrf_token'})
        if form_token:
            csrf_token = form_token.get('value')

    print(f"   CSRF Token found: {csrf_token[:20]}..." if csrf_token else "   No CSRF token!")

    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'csrf_token': csrf_token
    }

    login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"   Login response: {login_response.status_code}")

    if login_response.status_code != 302:
        print("   ❌ Login failed!")
        return False

    print("   ✅ Login successful")

    # Step 2: Find a HELD email to edit
    print("\n2. Finding HELD email to edit...")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find a HELD email
    cursor.execute("""
        SELECT id, subject, body_text
        FROM email_messages
        WHERE interception_status = 'HELD'
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        print("   No HELD emails found, creating one...")
        # Insert a test email
        cursor.execute("""
            INSERT INTO email_messages
            (message_id, sender, recipients, subject, body_text, interception_status, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            f"test_{int(time.time())}",
            "test@example.com",
            '["recipient@example.com"]',
            "Original Subject",
            "Original Body Text",
            "HELD",
            "PENDING"
        ))
        conn.commit()
        email_id = cursor.lastrowid
        original_subject = "Original Subject"
        original_body = "Original Body Text"
    else:
        email_id = row['id']
        original_subject = row['subject']
        original_body = row['body_text']

    print(f"   Email ID: {email_id}")
    print(f"   Original subject: {original_subject}")
    print(f"   Original body: {original_body[:50]}..." if original_body else "   Original body: None")

    # Step 3: Test GET route for edit modal
    print("\n3. Testing GET /email/<id>/edit route...")

    edit_get_response = session.get(f"{BASE_URL}/email/{email_id}/edit")
    print(f"   GET response: {edit_get_response.status_code}")

    if edit_get_response.status_code == 200:
        try:
            data = edit_get_response.json()
            print(f"   ✅ Edit modal data retrieved")
            print(f"   Has subject: {'subject' in data}")
            print(f"   Has body_text: {'body_text' in data}")
        except:
            # The route exists but might return HTML in test mode
            print(f"   ⚠️ GET route returns HTML (expected in test), continuing...")

    # Step 4: Edit via API
    print("\n4. Editing email via API...")

    # Get fresh CSRF token from any authenticated page
    dashboard = session.get(f"{BASE_URL}/dashboard")
    soup = BeautifulSoup(dashboard.text, 'html.parser')
    csrf_token = None

    # Try to find CSRF token in meta tag
    meta_tag = soup.find('meta', {'name': 'csrf-token'})
    if meta_tag:
        csrf_token = meta_tag.get('content')
        print(f"   CSRF token found: {csrf_token[:20]}...")
    else:
        print("   Warning: No CSRF token found in meta tag")

    new_subject = f"EDITED_SUBJECT_{int(time.time())}"
    new_body = f"EDITED_BODY_TEXT_{int(time.time())}"

    edit_data = {
        'subject': new_subject,
        'body_text': new_body
    }

    print(f"   New subject: {new_subject}")
    print(f"   New body: {new_body}")

    # Set the CSRF token in the header
    headers = {}
    if csrf_token:
        headers['X-CSRFToken'] = csrf_token

    edit_response = session.post(
        f"{BASE_URL}/api/email/{email_id}/edit",
        json=edit_data,
        headers=headers
    )

    print(f"   Edit response: {edit_response.status_code}")

    if edit_response.status_code == 200:
        response_data = edit_response.json()
        print(f"   Response: {json.dumps(response_data, indent=2)}")

        # Check verified field
        if 'verified' in response_data:
            verified = response_data['verified']
            print(f"   ✅ Server verified persistence:")
            print(f"      Subject: {verified.get('subject')}")
            print(f"      Body: {verified.get('body_text', '')[:50]}...")
    else:
        print(f"   ❌ Edit failed: {edit_response.text[:200]}")
        conn.close()
        return False

    # Step 5: Verify in database
    print("\n5. Verifying database persistence...")

    cursor.execute("""
        SELECT subject, body_text, updated_at
        FROM email_messages
        WHERE id = ?
    """, (email_id,))

    updated_row = cursor.fetchone()
    conn.close()

    if updated_row:
        db_subject = updated_row['subject']
        db_body = updated_row['body_text']
        db_updated = updated_row['updated_at']

        print(f"   DB Subject: {db_subject}")
        print(f"   DB Body: {db_body[:50] if db_body else 'None'}...")
        print(f"   Updated at: {db_updated}")

        subject_saved = (db_subject == new_subject)
        body_saved = (db_body == new_body)

        print()
        print("=" * 80)
        print("RESULTS:")
        print(f"   Subject saved: {'✅' if subject_saved else '❌'} {subject_saved}")
        print(f"   Body saved: {'✅' if body_saved else '❌'} {body_saved}")

        if subject_saved and body_saved:
            print("\n   🎉 SUCCESS! Email edit saves both subject AND body_text!")
            return True
        else:
            print("\n   ❌ FAILURE! Edit did not persist correctly")
            return False
    else:
        print("   ❌ Email not found in database!")
        return False

if __name__ == "__main__":
    import time
    success = test_edit_persistence()
    exit(0 if success else 1)