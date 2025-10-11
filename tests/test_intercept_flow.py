"""
Interception Lifecycle Tests:
1. Fetch stores original_uid + original_internaldate
2. Manual intercept sets HELD & latency_ms (with remote move)
3. Release sets RELEASED + DELIVERED
"""
import os
import sqlite3
import json
import types
import time
import pytest

os.environ['TEST_DB_PATH'] = 'test_intercept_flow.db'

from simple_app import app, init_database, DB_PATH as RUNTIME_DB_PATH  # simple_app reads TEST_DB_PATH via import

@pytest.fixture(scope="module", autouse=True)
def fresh_db():
    if os.path.exists(os.environ['TEST_DB_PATH']):
        os.remove(os.environ['TEST_DB_PATH'])
    init_database()
    yield
    try:
        os.remove(os.environ['TEST_DB_PATH'])
    except Exception:
        pass

def _ins(cur, sql, params):
    cur.execute(sql, params)
    return cur.lastrowid

def seed_account():
    conn = sqlite3.connect(os.environ['TEST_DB_PATH'])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO email_accounts
        (account_name, email_address, imap_host, imap_port, imap_username, imap_password, smtp_host, smtp_port, smtp_username, smtp_password, is_active)
        VALUES ('TestAcct','acct@example.com','imap.test.local',993,'acct@example.com','encrypted','smtp.test.local',587,'acct@example.com','encrypted',1)
    """)
    aid = cur.lastrowid
    conn.commit()
    conn.close()
    return aid

class FakeIMAP:
    def __init__(self, *a, **k):
        self._selected='INBOX'

    def login(self, *a, **k):
        return 'OK', []

    def select(self, mb):
        self._selected=mb
        return ('OK', [b'1'])

    def uid(self, cmd, *args):
        if cmd == 'search':
            return ('OK', [b'101 102'])
        if cmd == 'fetch':
            uid = args[0]
            # INTERNALDATE "01-Oct-2025 12:34:56 +0000"
            meta = f'{uid} (UID {uid} RFC822 {{10}} INTERNALDATE "01-Oct-2025 12:34:56 +0000")'.encode()
            raw = b"Subject: Test\r\nMessage-ID: <uid-"+uid.encode()+b"@test>\r\n\r\nBody"
            return ('OK', [(meta, raw)])
        if cmd == 'MOVE':
            return ('OK', [])
        if cmd == 'COPY':
            return ('OK', [])
        if cmd == 'STORE':
            return ('OK', [])
        return ('OK', [])

    def expunge(self):
        return 'OK', []

    def logout(self):
        return 'OK', []

def test_fetch_stores_uid_and_internaldate(monkeypatch):
    aid = seed_account()
    # Monkeypatch decrypt_credential to return plaintext
    monkeypatch.setattr('simple_app.decrypt_credential', lambda v: 'pass')
    monkeypatch.setattr('imaplib.IMAP4_SSL', lambda host, port: FakeIMAP())
    client = app.test_client()
    # Need login bypass (simulate logged-in user by monkeypatching login_required? simplest: set a session cookie via test login route if exists)
    # For brevity in this focused test, monkeypatch login_required decorator to pass
    monkeypatch.setattr('flask_login.utils._get_user', lambda: types.SimpleNamespace(is_authenticated=True, id=1, role='admin'))
    resp = client.post('/api/fetch-emails', json={'account_id': aid, 'count': 1})
    data = resp.get_json()
    assert data['success'] is True
    assert data['fetched'] == 1
    # Verify DB row has original_uid + original_internaldate
    conn = sqlite3.connect(os.environ['TEST_DB_PATH'])
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT original_uid, original_internaldate FROM email_messages WHERE interception_status='FETCHED' LIMIT 1").fetchone()
    conn.close()
    # Timezone may vary, just verify the date and that time exists
    assert row and row['original_uid'] and row['original_internaldate'].startswith('2025-10-01T')

def test_manual_intercept_moves_and_latency(monkeypatch):
    # Seed account + fetched row
    conn = sqlite3.connect(os.environ['TEST_DB_PATH'])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    aid = cur.execute("SELECT id FROM email_accounts LIMIT 1").fetchone()[0]
    cur.execute("""
        INSERT INTO email_messages
        (message_id, account_id, direction, interception_status, status, sender, recipients, subject, body_text, created_at)
        VALUES ('mid-1', ?, 'inbound', 'FETCHED', 'PENDING', 's@example.com', '["r@example.com"]', 'Subject A', 'Body', datetime('now','-2 minutes'))
    """, (aid,))
    email_id = cur.lastrowid
    conn.commit()
    conn.close()

    monkeypatch.setattr('app.utils.imap_helpers._imap_connect_account', lambda row: (FakeIMAP(), True))
    monkeypatch.setattr('app.utils.imap_helpers._move_uid_to_quarantine', lambda *a, **k: True)
    monkeypatch.setattr('simple_app.decrypt_credential', lambda v: 'pass')
    from simple_app import app as flask_app
    client = flask_app.test_client()
    monkeypatch.setattr('flask_login.utils._get_user', lambda: types.SimpleNamespace(is_authenticated=True, id=99, role='admin'))
    resp = client.post(f'/api/email/{email_id}/intercept')
    data = resp.get_json()
    assert data['success'] and data['remote_move'] is True

    conn = sqlite3.connect(os.environ['TEST_DB_PATH'])
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT interception_status, latency_ms FROM email_messages WHERE id=?", (email_id,)).fetchone()
    conn.close()
    assert row['interception_status'] == 'HELD'
    assert row['latency_ms'] is not None and row['latency_ms'] > 0

def test_release_sets_delivered(monkeypatch):
    # Prepare HELD message with account + simple raw_content
    conn = sqlite3.connect(os.environ['TEST_DB_PATH'])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    aid = cur.execute("SELECT id FROM email_accounts LIMIT 1").fetchone()[0]
    raw = b"Subject: HeldMail\r\nMessage-ID: <held@test>\r\n\r\nOriginal Body"
    cur.execute("""
        INSERT INTO email_messages
        (message_id, account_id, direction, interception_status, status, sender, recipients, subject, raw_content, created_at)
        VALUES ('held-1', ?, 'inbound', 'HELD', 'PENDING', 's@example.com', '["r@example.com"]', 'HeldMail', ?, datetime('now','-60 seconds'))
    """, (aid, raw))
    msg_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Patch decrypt + imap append (release endpoint in blueprint)
    class FakeReleaseIMAP(FakeIMAP):
        def append(self, folder, flags, internaldate, msg_bytes):
            return ('OK', [])

    monkeypatch.setattr('imaplib.IMAP4_SSL', lambda h, p: FakeReleaseIMAP())
    monkeypatch.setattr('app.routes.interception.decrypt_credential', lambda v: 'pass')
    monkeypatch.setattr('flask_login.utils._get_user', lambda: types.SimpleNamespace(is_authenticated=True, id=42, role='admin'))

    client = app.test_client()
    resp = client.post(f'/api/interception/release/{msg_id}', json={'edited_subject': 'Edited Held', 'edited_body': 'NewBody'})
    data = resp.get_json()
    assert data.get('ok') is True

    conn = sqlite3.connect(os.environ['TEST_DB_PATH'])
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT interception_status, status, edited_message_id FROM email_messages WHERE id=?", (msg_id,)).fetchone()
    conn.close()
    assert row['interception_status'] == 'RELEASED'
    assert row['status'] == 'DELIVERED'
    assert row['edited_message_id'] is not None
