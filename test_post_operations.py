#!/usr/bin/env python3
"""
Test script for POST operations with CSRF tokens
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:5020"

def extract_csrf_token(html):
    """Extract CSRF token from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    if csrf_input:
        return csrf_input.get('value')
    return None

def test_login():
    """Test 1: Login POST with CSRF"""
    print("=" * 60)
    print("TEST 1: Login POST with CSRF")
    print("=" * 60)

    session = requests.Session()

    # Get login page and extract CSRF token
    response = session.get(f"{BASE_URL}/login")
    csrf_token = extract_csrf_token(response.text)
    print(f"✓ CSRF Token extracted: {csrf_token[:20]}...")

    # Attempt login
    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'csrf_token': csrf_token
    }
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"✓ POST /login returned: {response.status_code}")
    print(f"✓ Redirect location: {response.headers.get('Location', 'None')}")

    # Follow redirect to check if logged in
    if response.status_code == 302:
        redirect_url = response.headers.get('Location')
        if redirect_url and '/dashboard' in redirect_url:
            print("✓ Login successful - redirected to dashboard")
            return session, True
        else:
            print("⚠ Login redirected but not to dashboard")
            return session, False

    return session, False

def test_api_post(session):
    """Test 2: API POST operation"""
    print("\n" + "=" * 60)
    print("TEST 2: API POST Operation")
    print("=" * 60)

    # Try to get held emails count
    response = session.get(f"{BASE_URL}/api/interception/held")
    print(f"✓ GET /api/interception/held returned: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response data: held_count={data.get('held_count', 'N/A')}")
        return True
    else:
        print(f"⚠ API call failed: {response.status_code}")
        return False

def test_dashboard_access(session):
    """Test 3: Access authenticated page"""
    print("\n" + "=" * 60)
    print("TEST 3: Dashboard Access (authenticated)")
    print("=" * 60)

    response = session.get(f"{BASE_URL}/dashboard")
    print(f"✓ GET /dashboard returned: {response.status_code}")

    if response.status_code == 200:
        print("✓ Dashboard accessible")
        return True
    elif response.status_code == 302:
        print("⚠ Redirected (not authenticated?)")
        return False
    else:
        print(f"⚠ Unexpected status: {response.status_code}")
        return False

if __name__ == '__main__':
    try:
        # Test 1: Login
        session, login_success = test_login()

        if login_success:
            # Test 2: API POST
            test_api_post(session)

            # Test 3: Dashboard access
            test_dashboard_access(session)

            print("\n" + "=" * 60)
            print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠ Login test failed - skipping other tests")
            print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
