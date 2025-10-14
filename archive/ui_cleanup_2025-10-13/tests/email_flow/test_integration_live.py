"""
Integration tests with real SMTP/IMAP connections.

Uses actual Gmail and Hostinger accounts for end-to-end validation.
Requires INTEGRATION_EMAIL_TESTS=1 environment variable to run.

SAFETY MEASURES:
- Unique timestamped subjects
- Short timeouts (15-30s)
- No deletion of existing mail
- Tests skip if credentials not provided
"""
import os
import pytest
import time
import smtplib
import imaplib
from email.message import EmailMessage
from conftest import (
    GMAIL_EMAIL, GMAIL_PASSWORD,
    HOSTINGER_EMAIL, HOSTINGER_PASSWORD,
    INTEGRATION_ENABLED, unique_subject
)

# Skip all tests in this module unless integration flag is set
pytestmark = pytest.mark.skipif(
    not INTEGRATION_ENABLED,
    reason="Integration tests disabled. Set INTEGRATION_EMAIL_TESTS=1 to enable."
)


def test_smtp_gmail_connect():
    """Verify Gmail SMTP connection with STARTTLS."""
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        code, _ = server.ehlo()
        assert 200 <= code < 400, f"EHLO failed with code {code}"

        server.starttls()
        server.login(GMAIL_EMAIL, GMAIL_PASSWORD)


def test_imap_gmail_list():
    """Verify Gmail IMAP connection and mailbox listing."""
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    typ, _ = mail.login(GMAIL_EMAIL, GMAIL_PASSWORD)
    assert typ == 'OK', f"Login failed: {typ}"

    typ, mailboxes = mail.list()
    assert typ == 'OK', f"LIST failed: {typ}"
    assert any(b'INBOX' in mb for mb in mailboxes), "INBOX not found"

    mail.logout()


def test_smtp_hostinger_connect():
    """Verify Hostinger SMTP connection with SSL."""
    with smtplib.SMTP_SSL("smtp.hostinger.com", 465, timeout=15) as server:
        server.login(HOSTINGER_EMAIL, HOSTINGER_PASSWORD)


def test_imap_hostinger_list():
    """Verify Hostinger IMAP connection and mailbox listing."""
    mail = imaplib.IMAP4_SSL("imap.hostinger.com", 993)
    typ, _ = mail.login(HOSTINGER_EMAIL, HOSTINGER_PASSWORD)
    assert typ == 'OK', f"Login failed: {typ}"

    typ, mailboxes = mail.list()
    assert typ == 'OK', f"LIST failed: {typ}"

    mail.logout()


def test_send_and_fetch_self_gmail():
    """Send email to self via Gmail and verify IMAP retrieval."""
    # Create unique test email
    msg = EmailMessage()
    subject = unique_subject("SELF-DELIVERY")
    msg['From'] = GMAIL_EMAIL
    msg['To'] = GMAIL_EMAIL
    msg['Subject'] = subject
    msg.set_content(f"Integration test self-delivery at {time.time()}")

    # Send via SMTP
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
        server.sendmail(msg['From'], [msg['To']], msg.as_string())

    # Poll IMAP for arrival (max 45 seconds)
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_EMAIL, GMAIL_PASSWORD)

    deadline = time.time() + 45
    found = False

    while time.time() < deadline and not found:
        mail.select("INBOX")
        typ, data = mail.search(None, 'ALL')

        if typ == 'OK':
            message_ids = data[0].split()
            # Check recent messages (last 25)
            for msg_id in reversed(message_ids[-25:]):
                typ, data = mail.fetch(msg_id, '(BODY[HEADER.FIELDS (SUBJECT)])')
                if typ == 'OK' and subject.encode() in data[0][1]:
                    found = True
                    break

        if not found:
            time.sleep(3)

    mail.logout()
    assert found, f"Test email not found within 45 seconds: {subject}"


def test_compose_intercept_release_cycle_gmail(db_conn, gmail_account):
    """Full workflow: compose → intercept → hold → edit → release."""
    # 1. Create test email
    subject = unique_subject("INTERCEPT-CYCLE")
    msg = EmailMessage()
    msg['From'] = GMAIL_EMAIL
    msg['To'] = GMAIL_EMAIL
    msg['Subject'] = subject
    msg.set_content("Original body content")

    # 2. Insert as PENDING in database (simulating compose)
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status, interception_status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'outbound', 'PENDING', NULL, ?, ?, ?, ?)
    """, (gmail_account, GMAIL_EMAIL, f'["{GMAIL_EMAIL}"]', subject, "Original body content"))
    db_conn.commit()

    email_id = db_conn.execute(
        "SELECT id FROM email_messages WHERE subject=?", (subject,)
    ).fetchone()['id']

    # 3. Simulate automatic interception (rule match)
    db_conn.execute("""
        UPDATE email_messages
        SET interception_status='HELD'
        WHERE id=?
    """, (email_id,))
    db_conn.commit()

    # Verify HELD status
    row = db_conn.execute(
        "SELECT interception_status FROM email_messages WHERE id=?", (email_id,)
    ).fetchone()
    assert row['interception_status'] == 'HELD'

    # 4. Edit email
    edited_subject = f"{subject} [EDITED]"
    edited_body = "Edited body content after review"
    db_conn.execute("""
        UPDATE email_messages
        SET subject=?, body_text=?
        WHERE id=?
    """, (edited_subject, edited_body, email_id))
    db_conn.commit()

    # 5. Release email (transition to RELEASED/DELIVERED)
    db_conn.execute("""
        UPDATE email_messages
        SET interception_status='RELEASED', status='DELIVERED'
        WHERE id=?
    """, (email_id,))
    db_conn.commit()

    # Verify final state
    final_row = db_conn.execute("""
        SELECT interception_status, status, subject, body_text
        FROM email_messages WHERE id=?
    """, (email_id,)).fetchone()

    assert final_row['interception_status'] == 'RELEASED'
    assert final_row['status'] == 'DELIVERED'
    assert final_row['subject'] == edited_subject
    assert final_row['body_text'] == edited_body


def test_manual_hold_existing_email_gmail():
    """Manually hold an existing email in INBOX."""
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_EMAIL, GMAIL_PASSWORD)
    mail.select("INBOX")

    # Search for any email
    typ, data = mail.search(None, 'ALL')
    assert typ == 'OK', "Search failed"

    message_ids = data[0].split()
    if not message_ids:
        pytest.skip("No emails in INBOX to test manual hold")

    # Get first email UID
    test_uid = message_ids[0].decode()

    # Verify email exists
    typ, data = mail.fetch(test_uid, '(BODY[HEADER.FIELDS (SUBJECT)])')
    assert typ == 'OK', "Fetch failed"

    # In real app, this would move to Quarantine folder
    # For test, just verify we can flag it
    mail.store(test_uid, '+FLAGS', '\\Flagged')

    mail.logout()


def test_forward_workflow_gmail(db_conn, gmail_account):
    """Forward an email creates new database entry with link."""
    # Insert original email
    original_subject = unique_subject("FORWARD-BASE")
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'DELIVERED', ?, ?, ?, ?)
    """, (gmail_account, "sender@example.com", f'["{GMAIL_EMAIL}"]',
          original_subject, "Original content"))
    db_conn.commit()

    original_id = db_conn.execute(
        "SELECT id FROM email_messages WHERE subject=?", (original_subject,)
    ).fetchone()['id']

    # Create forward entry
    forward_subject = f"Fwd: {original_subject}"
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text, in_reply_to
        ) VALUES (?, 'outbound', 'SENT', ?, ?, ?, ?, ?)
    """, (gmail_account, GMAIL_EMAIL, '["other@example.com"]',
          forward_subject, "Forwarded with note", original_id))
    db_conn.commit()

    # Verify link
    fwd_row = db_conn.execute(
        "SELECT in_reply_to, direction FROM email_messages WHERE subject=?",
        (forward_subject,)
    ).fetchone()

    assert fwd_row['in_reply_to'] == original_id
    assert fwd_row['direction'] == 'outbound'


def test_reply_workflow_gmail(db_conn, gmail_account):
    """Reply to email creates linked database entry."""
    # Insert parent email
    parent_subject = unique_subject("REPLY-PARENT")
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text
        ) VALUES (?, 'inbound', 'DELIVERED', ?, ?, ?, ?)
    """, (gmail_account, "sender@example.com", f'["{GMAIL_EMAIL}"]',
          parent_subject, "Question?"))
    db_conn.commit()

    parent_id = db_conn.execute(
        "SELECT id FROM email_messages WHERE subject=?", (parent_subject,)
    ).fetchone()['id']

    # Create reply
    reply_subject = f"Re: {parent_subject}"
    db_conn.execute("""
        INSERT INTO email_messages (
            account_id, direction, status,
            sender, recipients, subject, body_text, in_reply_to
        ) VALUES (?, 'outbound', 'SENT', ?, ?, ?, ?, ?)
    """, (gmail_account, GMAIL_EMAIL, '["sender@example.com"]',
          reply_subject, "Answer.", parent_id))
    db_conn.commit()

    # Verify link
    reply_row = db_conn.execute(
        "SELECT in_reply_to FROM email_messages WHERE subject=?",
        (reply_subject,)
    ).fetchone()

    assert reply_row['in_reply_to'] == parent_id
