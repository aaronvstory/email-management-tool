#!/usr/bin/env python3
"""Test email edit with proper authentication and CSRF token"""

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:5000"

def test_email_edit_with_auth():
    """Test editing an email with proper session authentication and CSRF token"""

    # Create session to maintain cookies
    session = requests.Session()

    # Step 1: Get login page and extract CSRF token
    print("1. Getting login page...")
    login_page = session.get(f"{BASE_URL}/")
    soup = BeautifulSoup(login_page.text, 'html.parser')

    # Find CSRF token (could be in meta tag or hidden input)
    csrf_token = None
    meta_tag = soup.find('meta', {'name': 'csrf-token'})
    if meta_tag:
        csrf_token = meta_tag.get('content')
    else:
        # Try hidden input
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = csrf_input.get('value')

    print(f"   CSRF Token found: {csrf_token[:20]}..." if csrf_token else "   No CSRF token found!")

    # Step 2: Login with credentials
    print("2. Logging in as admin...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }

    if csrf_token:
        login_data['csrf_token'] = csrf_token

    login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"   Login response: {login_response.status_code}")

    if login_response.status_code == 302:
        print(f"   Redirect to: {login_response.headers.get('Location')}")
        # Follow redirect
        session.get(f"{BASE_URL}{login_response.headers.get('Location')}")

    # Step 3: Get fresh CSRF token from authenticated page
    print("3. Getting authenticated CSRF token...")
    dashboard = session.get(f"{BASE_URL}/dashboard")
    soup = BeautifulSoup(dashboard.text, 'html.parser')

    csrf_token = None
    meta_tag = soup.find('meta', {'name': 'csrf-token'})
    if meta_tag:
        csrf_token = meta_tag.get('content')

    print(f"   Auth CSRF Token: {csrf_token[:20]}..." if csrf_token else "   No CSRF token in dashboard!")

    # Step 4: Test email edit API
    print("4. Testing email edit API...")

    # First, let's check what emails we have
    emails_response = session.get(f"{BASE_URL}/api/interception/held")
    if emails_response.status_code == 200:
        emails = emails_response.json()
        print(f"   API response type: {type(emails)}")

        # Handle different response formats
        if isinstance(emails, dict) and 'emails' in emails:
            emails_list = emails['emails']
        elif isinstance(emails, list):
            emails_list = emails
        else:
            emails_list = []

        if emails_list and len(emails_list) > 0:
            email_id = emails_list[0]['id']
            print(f"   Found email ID: {email_id}")

            # Try editing with CSRF token in header
            headers = {}
            if csrf_token:
                headers['X-CSRFToken'] = csrf_token

            edit_data = {
                'subject': 'Test Edit Subject',
                'body_text': 'Test edit body content'
            }

            edit_response = session.post(
                f"{BASE_URL}/api/email/{email_id}/edit",
                json=edit_data,
                headers=headers
            )

            print(f"   Edit response: {edit_response.status_code}")
            if edit_response.status_code == 200:
                print("   ✅ Email edit successful!")
                print(f"   Response: {edit_response.json()}")
            else:
                print(f"   ❌ Edit failed: {edit_response.text[:200]}")

                # Try with form data instead of JSON
                print("5. Retrying with form data...")
                if csrf_token:
                    edit_data['csrf_token'] = csrf_token

                edit_response = session.post(
                    f"{BASE_URL}/api/email/{email_id}/edit",
                    data=edit_data,
                    headers={'X-CSRFToken': csrf_token} if csrf_token else {}
                )

                print(f"   Edit response (form): {edit_response.status_code}")
                if edit_response.status_code == 200:
                    print("   ✅ Email edit successful with form data!")
                else:
                    print(f"   ❌ Still failed: {edit_response.text[:200]}")
        else:
            print("   No held emails found to test")
    else:
        print(f"   Failed to get emails: {emails_response.status_code}")

if __name__ == "__main__":
    test_email_edit_with_auth()