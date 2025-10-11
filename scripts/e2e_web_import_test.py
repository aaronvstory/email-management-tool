import io
import re
import json
from flask import Response
import os, sys
# Ensure app import from project root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from simple_app import app, init_database

# Make sure DB exists
init_database()

def get_csrf_token(html: str) -> str:
    m = re.search(r'name=\"csrf_token\"\s+value=\"([^\"]+)\"', html)
    return m.group(1) if m else ''


def run():
    client = app.test_client()

    # GET login page and extract CSRF token
    r = client.get('/login')
    assert r.status_code == 200, f"/login GET failed: {r.status_code}"
    token = get_csrf_token(r.get_data(as_text=True))
    assert token, "csrf_token not found on /login"

    # POST login
    r2 = client.post('/login', data={'username': 'admin', 'password': 'admin123', 'csrf_token': token}, follow_redirects=False)
    assert 300 <= r2.status_code < 400 and '/dashboard' in (r2.headers.get('Location') or ''), f"login failed: {r2.status_code} {r2.headers}"

    # Prepare CSV in-memory
    csv_bytes = io.BytesIO(b"email_address,imap_password,smtp_password\nquicktest@example.com,app-pass,app-pass\n")
    data = {
        'auto_detect': 'on',
        'file': (csv_bytes, 'quick.csv'),
    }

    # POST /api/accounts/import (CSRF-exempt)
    r3 = client.post('/api/accounts/import', data=data, content_type='multipart/form-data')
    assert r3.status_code == 200, f"import failed: {r3.status_code} {r3.data!r}"
    payload = r3.get_json() or {}
    assert payload.get('success') is True, f"import error: {json.dumps(payload)}"
    print("OK:", json.dumps(payload))


if __name__ == '__main__':
    run()
