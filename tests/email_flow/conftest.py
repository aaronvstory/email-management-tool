"""
Fixtures and configuration for email flow tests.

Provides:
- Test database with schema
- Mock SMTP/IMAP transports for unit tests
- Real account credentials for integration tests
- Helper functions for account setup
"""
import os
import sqlite3
import time
import imaplib
import smtplib
import pytest
from cryptography.fernet import Fernet

# Set test database path before any app imports
os.environ.setdefault("TEST_DB_PATH", "test_email_flow.sqlite")

# Real account credentials (from environment variables)
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "ndayijecika@gmail.com")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "bjormgplhgwkgpad")
HOSTINGER_EMAIL = os.getenv("HOSTINGER_EMAIL", "mcintyre@corrinbox.com")
HOSTINGER_PASSWORD = os.getenv("HOSTINGER_PASSWORD", "25Horses807$")

# Integration test control flag
INTEGRATION_ENABLED = os.getenv("INTEGRATION_EMAIL_TESTS", "0") == "1"


@pytest.fixture(scope="session")
def test_db_path():
    """Path to isolated test database."""
    return os.environ["TEST_DB_PATH"]


@pytest.fixture(autouse=True, scope="session")
def _clean_db(test_db_path):
    """Clean test database before and after session."""
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    yield
    try:
        os.remove(test_db_path)
    except OSError:
        pass


@pytest.fixture
def db_conn(test_db_path):
    """Provide test database connection with schema."""
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row

    # Create schema
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_messages (
            id INTEGER PRIMARY KEY,
            account_id INTEGER,
            direction TEXT,
            status TEXT,
            interception_status TEXT,
            sender TEXT,
            recipients TEXT,
            subject TEXT,
            body_text TEXT,
            body_html TEXT,
            raw_content BLOB,
            in_reply_to INTEGER,
            message_id TEXT,
            original_uid TEXT,
            internaldate TEXT,
            latency_ms INTEGER,
            risk_score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT,
            action_taken_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_accounts (
            id INTEGER PRIMARY KEY,
            account_name TEXT,
            email_address TEXT,
            imap_host TEXT,
            imap_port INTEGER,
            imap_username TEXT,
            imap_password TEXT,
            imap_use_ssl INTEGER,
            smtp_host TEXT,
            smtp_port INTEGER,
            smtp_username TEXT,
            smtp_password TEXT,
            smtp_use_ssl INTEGER,
            is_active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS interception_rules (
            id INTEGER PRIMARY KEY,
            account_id INTEGER,
            rule_type TEXT,
            pattern TEXT,
            action TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def encryption_key():
    """Generate test encryption key."""
    return Fernet.generate_key()


@pytest.fixture
def fernet(encryption_key):
    """Provide Fernet cipher for password encryption."""
    return Fernet(encryption_key)


def insert_account(conn, email, password, account_id, smtp_host, smtp_port, smtp_use_ssl,
                  imap_host, imap_port, encrypted_password):
    """Helper to insert test account with encrypted credentials."""
    conn.execute("""
        INSERT INTO email_accounts (
            id, account_name, email_address,
            imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
            smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl,
            is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        account_id, f"Test-{email.split('@')[0]}", email,
        imap_host, imap_port, email, encrypted_password, 1,
        smtp_host, smtp_port, email, encrypted_password, smtp_use_ssl
    ))
    conn.commit()
    return account_id


@pytest.fixture
def gmail_account(db_conn, fernet):
    """Insert Gmail test account into DB."""
    encrypted_pwd = fernet.encrypt(GMAIL_PASSWORD.encode()).decode()
    return insert_account(
        db_conn, GMAIL_EMAIL, GMAIL_PASSWORD, 3,
        "smtp.gmail.com", 587, 0,  # STARTTLS
        "imap.gmail.com", 993, encrypted_pwd
    )


@pytest.fixture
def hostinger_account(db_conn, fernet):
    """Insert Hostinger test account into DB."""
    encrypted_pwd = fernet.encrypt(HOSTINGER_PASSWORD.encode()).decode()
    return insert_account(
        db_conn, HOSTINGER_EMAIL, HOSTINGER_PASSWORD, 2,
        "smtp.hostinger.com", 465, 1,  # SSL direct
        "imap.hostinger.com", 993, encrypted_pwd
    )


@pytest.fixture
def mock_transports(monkeypatch):
    """Mock SMTP/IMAP for unit tests."""
    class DummySMTP:
        def __init__(self, host, port, timeout=10):
            self.host = host
            self.port = port
        def ehlo(self):
            return (250, b'OK')
        def starttls(self):
            return (220, b'Go ahead')
        def login(self, user, pwd):
            return (235, b'Authentication successful')
        def sendmail(self, sender, recipients, data):
            return {}
        def quit(self):
            return (221, b'Goodbye')
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class DummyIMAP:
        def __init__(self, host, port=None):
            self.host = host
            self.port = port
        def login(self, user, pwd):
            return ('OK', [b'Logged in'])
        def list(self):
            return ('OK', [b'(\\HasNoChildren) "/" INBOX', b'(\\HasNoChildren) "/" Quarantine'])
        def select(self, mailbox):
            return ('OK', [b'1'])
        def search(self, charset, *criteria):
            return ('OK', [b'1 2 3'])
        def fetch(self, message_set, parts):
            return ('OK', [(b'1', b'Dummy email content')])
        def store(self, message_set, command, flags):
            return ('OK', [b'1'])
        def copy(self, message_set, mailbox):
            return ('OK', [b'1'])
        def expunge(self):
            return ('OK', [b'1'])
        def append(self, mailbox, flags, date_time, message):
            return ('OK', [b'1'])
        def logout(self):
            return ('BYE', [])

    monkeypatch.setattr(smtplib, 'SMTP', DummySMTP)
    monkeypatch.setattr(smtplib, 'SMTP_SSL', DummySMTP)
    monkeypatch.setattr(imaplib, 'IMAP4_SSL', DummyIMAP)
    monkeypatch.setattr(imaplib, 'IMAP4', DummyIMAP)


def unique_subject(prefix="TEST"):
    """Generate unique subject with timestamp."""
    return f"{prefix}: Email Flow Test {int(time.time() * 1000)}"


def insert_rule(conn, account_id, pattern, action="HOLD"):
    """Helper to insert interception rule."""
    conn.execute("""
        INSERT INTO interception_rules (account_id, rule_type, pattern, action, is_active)
        VALUES (?, 'subject_contains', ?, ?, 1)
    """, (account_id, pattern, action))
    conn.commit()
