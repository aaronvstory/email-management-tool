"""
Complete Edit/Release Flow Test
Tests the entire interception → edit → release → verify pipeline
"""
import requests
from datetime import datetime
import sqlite3
import time
from app.services.imap_watcher import ImapWatcher, AccountConfig
from app.utils.crypto import decrypt_credential

BASE_URL = "http://localhost:5000"
DB_PATH = "email_manager.db"

def get_csrf_token(session):
    """Get CSRF token from login page"""
    response = session.get(f"{BASE_URL}/login")
    # Extract CSRF token from meta tag
    import re
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
    return match.group(1) if match else None

def login(session):
    """Login and get session cookie"""
    csrf_token = get_csrf_token(session)
    response = session.post(f"{BASE_URL}/login", data={
        "username": "admin",
        "password": "admin123",
        "csrf_token": csrf_token
    }, allow_redirects=False)
    return response.status_code in [200, 302]

def edit_email(session, email_id, new_body):
    """Edit email via API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    row = cursor.execute(f"SELECT subject FROM email_messages WHERE id={email_id}").fetchone()
    subject = row[0] if row else "Test"
    conn.close()

    response = session.post(
        f"{BASE_URL}/api/email/{email_id}/edit",
        json={
            "subject": subject,
            "body_text": new_body
        },
        headers={"Content-Type": "application/json"}
    )
    return response.status_code == 200, response.json()

def release_email(session, email_id):
    """Release email to INBOX"""
    response = session.post(
        f"{BASE_URL}/api/interception/release/{email_id}",
        json={"target_folder": "INBOX"},
        headers={"Content-Type": "application/json"}
    )
    return response.status_code == 200, response.json()

def check_imap_inbox():
    """Check IMAP INBOX for the released email"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.cursor().execute("SELECT id, email_address, imap_host, imap_port, imap_username, imap_password FROM email_accounts WHERE id=2").fetchone()
    conn.close()

    account_id, email, imap_host, imap_port, imap_username, imap_password = row
    password = decrypt_credential(imap_password)

    cfg = AccountConfig(
        imap_host=imap_host,
        imap_port=imap_port,
        username=imap_username or email,
        password=password,
        use_ssl=True
    )

    watcher = ImapWatcher(cfg)
    client = watcher._connect()

    if not client:
        return None

    try:
        client.select_folder('INBOX')
        uids = client.search(['FROM', 'ndayijecika@gmail.com', 'SUBJECT', 'INVOICE'])

        if not uids:
            return None

        # Get latest UID
        latest_uid = sorted([int(u) for u in uids])[-1]

        # Fetch full email
        fetch_data = client.fetch([latest_uid], ['RFC822'])
        raw_email = fetch_data[latest_uid][b'RFC822']

        from email import message_from_bytes, policy
        email_msg = message_from_bytes(raw_email, policy=policy.default)

        body = ""
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')

        watcher.close()

        return {
            'uid': latest_uid,
            'subject': str(email_msg.get('Subject', '')),
            'body': body
        }
    except Exception as e:
        print(f"Error checking IMAP: {e}")
        watcher.close()
        return None

def main():
    """Run complete test flow"""
    print("=" * 70)
    print("COMPLETE EDIT/RELEASE FLOW TEST")
    print("=" * 70)

    # Get email ID from database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    row = cursor.execute("""
        SELECT id, subject, body_text, interception_status, status
        FROM email_messages
        WHERE original_uid=126 AND account_id=2
    """).fetchone()
    conn.close()

    if not row:
        print("❌ Test email not found in database (UID 126)")
        return False

    email_id, subject, original_body, interception_status, status = row

    print(f"\\n📧 Found test email:")
    print(f"   ID: {email_id}")
    print(f"   Subject: {subject}")
    print(f"   Status: {interception_status}/{status}")
    print(f"   Original body preview: {original_body[:100]}...")

    # Step 1: Edit email
    print(f"\\n🔧 STEP 1: Edit email body with timestamp")
    edit_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_body = f"""{original_body}

--- EDITED VIA API ---
Edit timestamp: {edit_timestamp}
This text was added during the edit phase.
Only this edited version should appear in the INBOX.
--- END EDIT ---
"""

    session = requests.Session()
    if not login(session):
        print("❌ Login failed")
        return False

    success, response = edit_email(session, email_id, new_body)
    if success:
        print(f"✅ Email edited successfully")
        print(f"   Edit timestamp: {edit_timestamp}")
    else:
        print(f"❌ Edit failed: {response}")
        return False

    # Step 2: Release email
    print(f"\\n🚀 STEP 2: Release edited email to INBOX")
    success, response = release_email(session, email_id)
    if success:
        print(f"✅ Email released successfully")
    else:
        print(f"❌ Release failed: {response}")
        return False

    # Wait for IMAP operation to complete
    print(f"\\n⏳ Waiting 5 seconds for IMAP operation to complete...")
    time.sleep(5)

    # Step 3: Verify edited version in INBOX
    print(f"\\n🔍 STEP 3: Verify edited version in INBOX")
    inbox_email = check_imap_inbox()

    if not inbox_email:
        print("❌ Could not fetch email from INBOX")
        return False

    print(f"✅ Found email in INBOX:")
    print(f"   UID: {inbox_email['uid']}")
    print(f"   Subject: {inbox_email['subject']}")

    # Check if edited content is present
    if edit_timestamp in inbox_email['body']:
        print(f"\\n✅ SUCCESS: Edited version confirmed in INBOX")
        print(f"   Edit timestamp found: {edit_timestamp}")
        print(f"   Body preview: {inbox_email['body'][:200]}...")
        return True
    else:
        print(f"\\n❌ FAIL: Edit timestamp not found in INBOX email")
        print(f"   Expected: {edit_timestamp}")
        print(f"   Got: {inbox_email['body'][:200]}...")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\\n{'=' * 70}")
    print(f"TEST RESULT: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"{'=' * 70}")
    exit(0 if success else 1)
