import sqlite3
from uuid import uuid4
import pytest

from app.services.imap_watcher import ImapWatcher, AccountConfig
from app.utils.db import DB_PATH


@pytest.fixture()
def temp_account():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    acct_name = f"CBTest_{uuid4().hex[:8]}"
    cur.execute(
        """
        INSERT INTO email_accounts (account_name, email_address, imap_host, imap_port, imap_username, imap_password,
            imap_use_ssl, smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl, is_active)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            acct_name,
            'cb@example.com',
            'imap.invalid',
            993,
            'cb@example.com',
            'dummy',
            1,
            'smtp.invalid',
            587,
            'cb@example.com',
            'dummy',
            0,
            1,
        ),
    )
    acc_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        yield acc_id
    finally:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM email_accounts WHERE id=?", (acc_id,))
        # cleanup worker heartbeat
        cur.execute("DELETE FROM worker_heartbeats WHERE worker_id=?", (f"imap_{acc_id}",))
        conn.commit(); conn.close()


def test_circuit_breaker_disables_account_after_failures(temp_account):
    acc_id = temp_account
    cfg = AccountConfig(imap_host='imap.invalid', username='cb@example.com', password='x', account_id=acc_id, db_path=DB_PATH)
    watcher = ImapWatcher(cfg)
    # Simulate N failures
    for _ in range(5):
        watcher._record_failure('auth_failed')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    is_active = cur.execute("SELECT is_active FROM email_accounts WHERE id=?", (acc_id,)).fetchone()[0]
    last_error = cur.execute("SELECT last_error FROM email_accounts WHERE id=?", (acc_id,)).fetchone()[0]
    err_count = cur.execute("SELECT error_count FROM worker_heartbeats WHERE worker_id=?", (f"imap_{acc_id}",)).fetchone()[0]
    conn.close()

    assert is_active == 0
    assert isinstance(last_error, str) and 'circuit_open' in last_error
    assert err_count >= 5
