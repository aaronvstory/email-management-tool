#!/usr/bin/env python3
"""Test editing specific email ID 226 with authentication"""

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:5000"
EMAIL_ID = 226  # Known held email

def test_edit_email_226():
    """Test editing email 226 with proper authentication"""

    session = requests.Session()

    # Step 1: Login
    print("1. Logging in...")
    login_page = session.get(f"{BASE_URL}/")
    soup = BeautifulSoup(login_page.text, 'html.parser')

    csrf_token = None
    meta_tag = soup.find('meta', {'name': 'csrf-token'})
    if meta_tag:
        csrf_token = meta_tag.get('content')

    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }

    if csrf_token:
        login_data['csrf_token'] = csrf_token

    login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"   Login status: {login_response.status_code}")

    if login_response.status_code == 302:
        session.get(f"{BASE_URL}/dashboard")

    # Step 2: Get authenticated CSRF token
    print("2. Getting authenticated CSRF token...")
    dashboard = session.get(f"{BASE_URL}/dashboard")
    soup = BeautifulSoup(dashboard.text, 'html.parser')

    csrf_token = None
    meta_tag = soup.find('meta', {'name': 'csrf-token'})
    if meta_tag:
        csrf_token = meta_tag.get('content')
        print(f"   CSRF Token: {csrf_token[:20]}...")

    # Step 3: Test different edit approaches
    print(f"3. Testing edit of email {EMAIL_ID}...")

    # Approach 1: JSON with CSRF header
    print("   A. Trying JSON with X-CSRFToken header...")
    headers = {}
    if csrf_token:
        headers['X-CSRFToken'] = csrf_token
        headers['X-CSRF-Token'] = csrf_token  # Try both variants

    edit_data = {
        'subject': 'EDITED: Test Subject',
        'body_text': 'This email was successfully edited via API'
    }

    response = session.post(
        f"{BASE_URL}/api/email/{EMAIL_ID}/edit",
        json=edit_data,
        headers=headers
    )
    print(f"      Response: {response.status_code}")
    if response.status_code != 200:
        print(f"      Error: {response.text[:100]}")

    # Approach 2: Form data with CSRF token
    if response.status_code != 200:
        print("   B. Trying form data with csrf_token field...")
        form_data = {
            'subject': 'EDITED: Test Subject',
            'body_text': 'This email was successfully edited via API',
            'csrf_token': csrf_token
        }

        response = session.post(
            f"{BASE_URL}/api/email/{EMAIL_ID}/edit",
            data=form_data
        )
        print(f"      Response: {response.status_code}")
        if response.status_code != 200:
            print(f"      Error: {response.text[:100]}")

    # Approach 3: Check if API endpoint exists
    if response.status_code != 200:
        print("   C. Checking if endpoint exists...")
        response = session.get(f"{BASE_URL}/api/email/{EMAIL_ID}/edit")
        print(f"      GET Response: {response.status_code}")

    # Step 4: Verify via database
    print("\n4. Checking database for changes...")
    import sqlite3
    conn = sqlite3.connect('email_manager.db')
    cursor = conn.cursor()
    result = cursor.execute(
        "SELECT subject, body_text FROM email_messages WHERE id = ?",
        (EMAIL_ID,)
    ).fetchone()
    conn.close()

    if result:
        print(f"   Current subject: {result[0]}")
        print(f"   Body preview: {result[1][:50] if result[1] else 'None'}...")
        if "EDITED:" in str(result[0]):
            print("   ✅ Email was successfully edited!")
        else:
            print("   ❌ Email was not edited")
    else:
        print(f"   Email {EMAIL_ID} not found in database")

if __name__ == "__main__":
    test_edit_email_226()