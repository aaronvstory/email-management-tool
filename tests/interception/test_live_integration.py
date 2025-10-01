"""Optional live integration test for interception pipeline.

This test is skipped unless required environment variables are present:
  IMAP_TEST_HOST, IMAP_TEST_USER, IMAP_TEST_PASS

It will:
 1. Connect to IMAP and APPEND a synthetic message into INBOX.
 2. Wait a short window for the rapid interception worker (external run) to copy+purge it.
 3. Assert a HELD row appears in email_messages with raw_path populated (eventually).

NOTE: The interception worker must be running separately for this to pass.
If not running, the test will xfail after timeout.
"""
import os
import time
import imaplib
import sqlite3
import pytest
from email.message import EmailMessage
from datetime import datetime

DB_PATH = 'email_manager.db'
REQUIRED_VARS = ['IMAP_TEST_HOST','IMAP_TEST_USER','IMAP_TEST_PASS']

@pytest.mark.skipif(any(os.environ.get(v) is None for v in REQUIRED_VARS), reason="Live IMAP env vars missing")
def test_live_interception_roundtrip():
    host = os.environ['IMAP_TEST_HOST']
    user = os.environ['IMAP_TEST_USER']
    password = os.environ['IMAP_TEST_PASS']
    port = int(os.environ.get('IMAP_TEST_PORT','993'))
    use_ssl = os.environ.get('IMAP_TEST_SSL','1') != '0'

    # Craft message
    msg = EmailMessage()
    msg['From'] = user
    msg['To'] = user
    unique_subject = f"InterceptionTest {datetime.utcnow().isoformat()}"
    msg['Subject'] = unique_subject
    msg.set_content('This is a live interception test message.')

    if use_ssl:
        imap = imaplib.IMAP4_SSL(host, port)
    else:
        imap = imaplib.IMAP4(host, port)
    imap.login(user, password)
    imap.append('INBOX', '', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    imap.logout()

    # Poll database for interception record
    deadline = time.time() + 30  # up to 30s (should usually be <2s)
    found = None
    raw_path = None
    while time.time() < deadline:
        if not os.path.exists(DB_PATH):
            time.sleep(0.5)
            continue
        conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        row = cur.execute("""
            SELECT id, subject, interception_status, raw_path
            FROM email_messages
            WHERE direction='inbound' AND interception_status='HELD' AND subject LIKE ?
            ORDER BY id DESC LIMIT 1
        """, (f"%{unique_subject}%",)).fetchone()
        conn.close()
        if row:
            found = row
            raw_path = row['raw_path']
            if raw_path and os.path.exists(raw_path):
                break
        time.sleep(1)

    if not found:
        pytest.xfail("Message not intercepted within timeout (worker not running?)")

    assert found['interception_status'] == 'HELD'
    assert raw_path is not None, "raw_path not yet populated"
    assert os.path.exists(raw_path), "raw file missing on disk"
