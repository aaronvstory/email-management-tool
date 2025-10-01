"""E2E (DB-level) edit-before-release flow test.

This test simulates an intercepted (HELD) inbound email entirely via the database
to exercise the JSON edit + release endpoints without requiring a live IMAP
server or the running interception worker.

Flow:
 1. Insert a synthetic HELD inbound email_messages row with raw_path pointing to a temp .eml file.
 2. Call /api/email/<id>/edit to modify subject and body_text.
 3. Mock (or bypass) actual IMAP APPEND by monkeypatching imaplib.IMAP4/IMAP4_SSL login & append
    so release endpoint can proceed without network.
 4. Call /api/interception/release/<id> with edited_subject/body.
 5. Assert DB row updated to interception_status=RELEASED and subject persisted.

NOTE: This focuses on application logic; the actual APPEND is mocked to avoid external dependency.
"""
import os
import sqlite3
import tempfile
from email.message import EmailMessage
from datetime import datetime

import pytest
from flask import Flask

DB_PATH = 'email_manager.db'

@pytest.fixture()
def app_client(monkeypatch):
    # Import the app after ensuring DB exists
    import simple_app as sa  # simple_app defines 'app'

    # Monkeypatch imaplib to avoid real network
    import imaplib
    class DummyIMAP:
        def __init__(self, host, port):
            self.host = host; self.port = port
        def login(self, user, pwd):
            return 'OK', []
        def select(self, folder):
            return ('OK', [b'1'])
        def append(self, mailbox, flags, internaldate, msg_bytes):
            # accept all appends
            return 'OK', []
        def logout(self):
            return 'BYE', []
    monkeypatch.setattr(imaplib, 'IMAP4_SSL', DummyIMAP)
    monkeypatch.setattr(imaplib, 'IMAP4', DummyIMAP)

    sa.app.config['TESTING'] = True
    client = sa.app.test_client()
    return client

def _ensure_tables():
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Ensure required columns exist (lightweight – assumes schema initialized elsewhere)
    conn.close()

def test_edit_then_release(app_client, tmp_path):
    _ensure_tables()

    # Build raw email file
    msg = EmailMessage()
    msg['From'] = 'sender@example.com'
    msg['To'] = 'recipient@example.com'
    original_subject = f"HeldTest {datetime.utcnow().isoformat()}"
    msg['Subject'] = original_subject
    msg.set_content('Original body text')
    raw_file = tmp_path / 'held_original.eml'
    raw_file.write_bytes(msg.as_bytes())

    # Insert a synthetic account (if needed) & email row
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    # Minimal account for join in release
    cur.execute("""
        INSERT INTO email_accounts (account_name, email_address, imap_host, imap_port, imap_username, imap_password,
            imap_use_ssl, smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl, is_active)
        VALUES ('TestAcct','sender@example.com','imap.local',993,'sender@example.com','dummy',1,'smtp.local',587,'sender@example.com','dummy',0,1)
    """)
    account_id = cur.lastrowid

    cur.execute("""
        INSERT INTO email_messages (direction, interception_status, account_id, sender, recipients, subject, body_text, raw_path, created_at)
        VALUES ('inbound','HELD',?,?,?,?,?,?,datetime('now'))
    """, (account_id,'sender@example.com','["recipient@example.com"]',original_subject,'Original body text', str(raw_file)))
    email_id = cur.lastrowid
    conn.commit(); conn.close()

    # Edit via API
    r = app_client.post(f"/api/email/{email_id}/edit", json={
        'subject': 'Edited Subject',
        'body_text': 'Edited body'
    })
    assert r.status_code == 200, r.data
    assert r.json['ok'] is True

    # Release via API
    r2 = app_client.post(f"/api/interception/release/{email_id}", json={
        'edited_subject': 'Edited Subject Final',
        'edited_body': 'Edited body final'
    })
    assert r2.status_code == 200, r2.data
    assert r2.json['ok'] is True

    # Validate DB state
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    row = cur.execute("SELECT interception_status, subject, body_text FROM email_messages WHERE id=?", (email_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row['interception_status'] == 'RELEASED'
    # Subject should reflect last edit (edit endpoint or release) – we updated DB in edit, release doesn't change 'subject' field directly; ensure it kept edit
    assert 'Edited Subject' in row['subject']
