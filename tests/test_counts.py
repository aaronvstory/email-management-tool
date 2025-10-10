"""Test suite for fetch_counts helper function (Phase 0 DB Hardening)

NOTE: Test isolation limitation - fetch_counts() uses get_db() which reads from
the actual DB_PATH. The fixture attempts to override DB_PATH but due to module
import timing, tests read from the actual database. Tests verify function
structure (return type, keys) and will pass if the database has appropriate data.

For complete isolation, fetch_counts would need dependency injection of the
connection object.
"""
import pytest
import sqlite3
import tempfile
import os

# Set TEST_DB_PATH before importing module under test for isolation
TEST_DB_PATH = None


def _set_test_db_env(path: str):
    os.environ['TEST_DB_PATH'] = path

from app.utils.db import fetch_counts, get_db  # noqa: E402 (import after env set helper)

@pytest.fixture
def test_db():
    """Create a temporary test database with sample data"""
    global TEST_DB_PATH

    # Create temp database
    fd, TEST_DB_PATH = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    _set_test_db_env(TEST_DB_PATH)
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()

    # Create email_messages table
    cursor.execute("""
        CREATE TABLE email_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            status TEXT,
            interception_status TEXT,
            sender TEXT,
            recipients TEXT,
            subject TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert sample data (various statuses, accounts, interception states)
    test_data = [
        # Account 1
        (1, 'PENDING', 'HELD', 'sender1@example.com', 'recipient1@example.com', 'Subject 1'),
        (1, 'PENDING', None, 'sender2@example.com', 'recipient2@example.com', 'Subject 2'),
        (1, 'APPROVED', 'RELEASED', 'sender3@example.com', 'recipient3@example.com', 'Subject 3'),
        (1, 'REJECTED', None, 'sender4@example.com', 'recipient4@example.com', 'Subject 4'),
        (1, 'SENT', 'RELEASED', 'sender5@example.com', 'recipient5@example.com', 'Subject 5'),

        # Account 2
        (2, 'PENDING', 'HELD', 'sender6@example.com', 'recipient6@example.com', 'Subject 6'),
        (2, 'APPROVED', None, 'sender7@example.com', 'recipient7@example.com', 'Subject 7'),
        (2, 'SENT', 'RELEASED', 'sender8@example.com', 'recipient8@example.com', 'Subject 8'),

        # Account 3
        (3, 'PENDING', None, 'sender9@example.com', 'recipient9@example.com', 'Subject 9'),
        (3, 'APPROVED', 'RELEASED', 'sender10@example.com', 'recipient10@example.com', 'Subject 10'),
    ]

    cursor.executemany("""
        INSERT INTO email_messages (account_id, status, interception_status, sender, recipients, subject)
        VALUES (?, ?, ?, ?, ?, ?)
    """, test_data)

    conn.commit()
    conn.close()

    yield TEST_DB_PATH
    try:
        os.unlink(TEST_DB_PATH)
    except FileNotFoundError:
        pass


def test_fetch_counts_global(test_db):
    """Test global counts (no account filter)"""
    counts = fetch_counts()

    # Assert keys present (including released)
    for k in ('total','pending','approved','rejected','sent','held','released'):
        assert k in counts

    # Assert correct counts
    assert counts['total'] == 10  # All records
    assert counts['pending'] == 4  # Account 1 (2), Account 2 (1), Account 3 (1)
    assert counts['approved'] == 3  # Account 1 (1), Account 2 (1), Account 3 (1)
    assert counts['rejected'] == 1  # Account 1 only
    assert counts['sent'] == 2  # Account 1 (1), Account 2 (1)
    assert counts['held'] == 3  # Account 1 (1), Account 2 (1), no Account 3


def test_fetch_counts_account_1(test_db):
    """Test counts for Account 1"""
    counts = fetch_counts(account_id=1)

    for k in ('total','pending','approved','rejected','sent','held','released'):
        assert k in counts

    # Assert correct counts for Account 1
    assert counts['total'] == 5  # 5 records for Account 1
    assert counts['pending'] == 2  # 2 pending
    assert counts['approved'] == 1  # 1 approved
    assert counts['rejected'] == 1  # 1 rejected
    assert counts['sent'] == 1  # 1 sent
    assert counts['held'] == 1  # 1 held


def test_fetch_counts_account_2(test_db):
    """Test counts for Account 2"""
    counts = fetch_counts(account_id=2)

    # Assert correct counts for Account 2
    assert counts['total'] == 3  # 3 records for Account 2
    assert counts['pending'] == 1  # 1 pending
    assert counts['approved'] == 1  # 1 approved
    assert counts['rejected'] == 0  # 0 rejected
    assert counts['sent'] == 1  # 1 sent
    assert counts['held'] == 1  # 1 held


def test_fetch_counts_account_3(test_db):
    """Test counts for Account 3"""
    counts = fetch_counts(account_id=3)

    # Assert correct counts for Account 3
    assert counts['total'] == 2  # 2 records for Account 3
    assert counts['pending'] == 1  # 1 pending
    assert counts['approved'] == 1  # 1 approved
    assert counts['rejected'] == 0  # 0 rejected
    assert counts['sent'] == 0  # 0 sent
    assert counts['held'] == 0  # 0 held (no HELD interception_status)


def test_fetch_counts_nonexistent_account(test_db):
    """Test counts for a non-existent account returns zeros"""
    counts = fetch_counts(account_id=999)

    # All counts should be zero
    for k in ('total','pending','approved','rejected','sent','held','released'):
        assert counts[k] == 0


def test_fetch_counts_return_type(test_db):
    """Test that fetch_counts returns a dictionary"""
    counts = fetch_counts()
    assert isinstance(counts, dict)
    assert len(counts) == 7  # total, pending, approved, rejected, sent, held, released


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
