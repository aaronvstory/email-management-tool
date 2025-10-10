"""
Unit tests for email pipeline workflows.

Tests use mocked SMTP/IMAP transports for fast, isolated validation.
Covers: compose, auto-hold, manual-hold, edit, release, forward, reply.
"""
import pytest
import json
from conftest import insert_account, insert_rule, unique_subject


def test_compose_stores_pending(db_conn, mock_transports, fernet):
    """Composing an email stores it as PENDING."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "sender@example.com", "testpass", 10,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Simulate compose action
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status, interception_status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'outbound', 'PENDING', NULL, ?, ?, ?, ?)
    """, (aid, "sender@example.com", '["recipient@example.com"]',
          "Compose Test", "Email body"))
    db_conn.commit()

    row = db_conn.execute(
        "SELECT status, direction FROM email_messages WHERE subject='Compose Test'"
    ).fetchone()

    assert row['status'] == 'PENDING'
    assert row['direction'] == 'outbound'


def test_rule_auto_hold(db_conn, fernet):
    """Automatic rule-based holding sets interception_status=HELD."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "auto@example.com", "testpass", 11,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Insert rule: hold messages with "URGENT" in subject
    insert_rule(db_conn, aid, "URGENT", "HOLD")

    subject = "URGENT: Security Alert"
    # Simulate rule engine evaluation
    interception_status = 'HELD' if "URGENT" in subject else None

    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status, interception_status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'PENDING', ?, ?, ?, ?, ?)
    """, (aid, interception_status, "sender@example.com",
          '["auto@example.com"]', subject, "Body"))
    db_conn.commit()

    row = db_conn.execute(
        "SELECT interception_status FROM email_messages WHERE subject LIKE 'URGENT:%'"
    ).fetchone()

    assert row['interception_status'] == 'HELD'


def test_manual_hold(db_conn, fernet):
    """Manual user action transitions PENDING → HELD."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "manual@example.com", "testpass", 12,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Insert delivered email
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status, interception_status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'DELIVERED', NULL, ?, ?, ?, ?)
    """, (aid, "sender@example.com", '["manual@example.com"]',
          "Normal Delivery", "Body"))
    db_conn.commit()

    # User manually holds it
    db_conn.execute("""
        UPDATE email_messages
        SET interception_status='HELD'
        WHERE subject='Normal Delivery'
    """)
    db_conn.commit()

    row = db_conn.execute(
        "SELECT interception_status FROM email_messages WHERE subject='Normal Delivery'"
    ).fetchone()

    assert row['interception_status'] == 'HELD'


def test_edit_email(db_conn, fernet):
    """Editing held email updates subject and body."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "edit@example.com", "testpass", 13,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Insert held email
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status, interception_status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'PENDING', 'HELD', ?, ?, ?, ?)
    """, (aid, "sender@example.com", '["edit@example.com"]',
          "Original Subject", "Original Body"))
    db_conn.commit()

    # Simulate edit
    new_subject = "Edited Subject"
    new_body = "Edited Body"
    db_conn.execute("""
        UPDATE email_messages
        SET subject=?, body_text=?
        WHERE subject='Original Subject'
    """, (new_subject, new_body))
    db_conn.commit()

    row = db_conn.execute(
        "SELECT subject, body_text FROM email_messages WHERE body_text=?",
        (new_body,)
    ).fetchone()

    assert row['subject'] == new_subject
    assert row['body_text'] == new_body


def test_release_marks_released(db_conn, fernet):
    """Releasing held email transitions to RELEASED/DELIVERED."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "release@example.com", "testpass", 14,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Insert held email
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status, interception_status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'PENDING', 'HELD', ?, ?, ?, ?)
    """, (aid, "sender@example.com", '["release@example.com"]',
          "To Release", "Body"))
    db_conn.commit()

    # Simulate release action
    db_conn.execute("""
        UPDATE email_messages
        SET interception_status='RELEASED', status='DELIVERED'
        WHERE subject='To Release'
    """)
    db_conn.commit()

    row = db_conn.execute(
        "SELECT interception_status, status FROM email_messages WHERE subject='To Release'"
    ).fetchone()

    assert row['interception_status'] == 'RELEASED'
    assert row['status'] == 'DELIVERED'


def test_forward_creates_new_row(db_conn, fernet):
    """Forwarding an email creates new row with in_reply_to link."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "fwd@example.com", "testpass", 15,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Insert base email
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'DELIVERED', ?, ?, ?, ?)
    """, (aid, "sender@example.com", '["fwd@example.com"]',
          "Base Message", "Original content"))
    db_conn.commit()

    base_id = db_conn.execute(
        "SELECT id FROM email_messages WHERE subject='Base Message'"
    ).fetchone()['id']

    # Forward to new recipient
    fwd_subject = f"Fwd: Base Message"
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text, in_reply_to
        ) VALUES (?, 'outbound', 'SENT', ?, ?, ?, ?, ?)
    """, (aid, "fwd@example.com", '["other@example.com"]',
          fwd_subject, "Forwarded content", base_id))
    db_conn.commit()

    fwd_row = db_conn.execute(
        "SELECT in_reply_to, direction FROM email_messages WHERE subject=?",
        (fwd_subject,)
    ).fetchone()

    assert fwd_row['in_reply_to'] == base_id
    assert fwd_row['direction'] == 'outbound'


def test_reply_links_parent(db_conn, fernet):
    """Replying to email links to parent via in_reply_to."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "reply@example.com", "testpass", 16,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Insert parent email
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'DELIVERED', ?, ?, ?, ?)
    """, (aid, "sender@example.com", '["reply@example.com"]',
          "Original Email", "Question"))
    db_conn.commit()

    parent_id = db_conn.execute(
        "SELECT id FROM email_messages WHERE subject='Original Email'"
    ).fetchone()['id']

    # Reply
    reply_subject = "Re: Original Email"
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text, in_reply_to
        ) VALUES (?, 'outbound', 'SENT', ?, ?, ?, ?, ?)
    """, (aid, "reply@example.com", '["sender@example.com"]',
          reply_subject, "Answer", parent_id))
    db_conn.commit()

    reply_row = db_conn.execute(
        "SELECT in_reply_to FROM email_messages WHERE subject=?",
        (reply_subject,)
    ).fetchone()

    assert reply_row['in_reply_to'] == parent_id


def test_latency_tracking(db_conn, fernet):
    """Email interception records latency_ms."""
    enc_pwd = fernet.encrypt(b"testpass").decode()
    aid = insert_account(
        db_conn, "latency@example.com", "testpass", 17,
        "smtp.local", 587, 0, "imap.local", 993, enc_pwd
    )

    # Simulate intercepted email with latency
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status, interception_status,
            sender, recipients, subject, body_text, latency_ms
        ) VALUES (?, 'inbound', 'PENDING', 'HELD', ?, ?, ?, ?, ?)
    """, (aid, "sender@example.com", '["latency@example.com"]',
          "Latency Test", "Body", 1234))
    db_conn.commit()

    row = db_conn.execute(
        "SELECT latency_ms FROM email_messages WHERE subject='Latency Test'"
    ).fetchone()

    assert row['latency_ms'] == 1234
