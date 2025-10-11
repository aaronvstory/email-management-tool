#!/usr/bin/env python3
"""Debug CSRF token extraction"""

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:5000"

# Create session
session = requests.Session()

# Step 1: Login
print("1. Getting login page...")
login_page = session.get(f"{BASE_URL}/")
soup = BeautifulSoup(login_page.text, 'html.parser')

# Find CSRF token in login page
csrf_token = None
meta_tag = soup.find('meta', {'name': 'csrf-token'})
if meta_tag:
    csrf_token = meta_tag.get('content')
    print(f"   Login page CSRF: {csrf_token[:20]}...")

# Look for form field too
form_token = soup.find('input', {'name': 'csrf_token'})
if form_token:
    csrf_token = form_token.get('value')
    print(f"   Form CSRF: {csrf_token[:20]}...")

if not csrf_token:
    print("   No CSRF token found!")

# Step 2: Login
login_data = {
    'username': 'admin',
    'password': 'admin123',
    'csrf_token': csrf_token
}

login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
print(f"2. Login response: {login_response.status_code}")

if login_response.status_code == 302:
    print("   ✅ Login successful")

# Step 3: Get dashboard
print("\n3. Getting dashboard page...")
dashboard = session.get(f"{BASE_URL}/dashboard")
soup = BeautifulSoup(dashboard.text, 'html.parser')

# Check for CSRF in dashboard
meta_tag = soup.find('meta', {'name': 'csrf-token'})
if meta_tag:
    csrf_token = meta_tag.get('content')
    print(f"   Dashboard CSRF found: {csrf_token[:20]}...")
else:
    print("   No CSRF in dashboard meta tags")

# Check if we're still logged in
if "Logout" in dashboard.text:
    print("   ✅ Still authenticated")
else:
    print("   ❌ Not authenticated")

# Save dashboard HTML for inspection
with open("dashboard_debug.html", "w", encoding="utf-8") as f:
    f.write(dashboard.text)
print("\n4. Dashboard HTML saved to dashboard_debug.html")

# Look for any script that sets CSRF
scripts = soup.find_all('script')
for i, script in enumerate(scripts):
    if 'csrf' in str(script).lower():
        print(f"   Found CSRF in script {i}")