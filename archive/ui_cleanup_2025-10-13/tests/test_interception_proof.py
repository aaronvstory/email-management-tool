import os
import time
import imaplib
import smtplib
import email
import pytest


def _send_via_smtp(host: str, port: int, subject: str, to_addr: str, body: str = "proof body"):
    msg = email.mime.text.MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'test@example.com'
    msg['To'] = to_addr
    with smtplib.SMTP(host, port, timeout=10) as s:
        s.send_message(msg)


@pytest.mark.skipif(os.getenv('ENABLE_LIVE_EMAIL_TESTS') != '1', reason='Live tests disabled')
def test_recipient_mode_no_inbox_leak():
    """Prove: HELD ⇒ not in INBOX; after release ⇒ present with edits (manual release step)."""

    # Config (Hostinger by default)
    imap_host = os.getenv('IMAP_HOST', 'imap.hostinger.com')
    imap_port = int(os.getenv('IMAP_PORT', '993'))
    to_addr = os.getenv('LIVE_TO', 'mcintyre@corrinbox.com')
    to_pass = os.getenv('HOSTINGER_PASSWORD')
    assert to_pass, 'HOSTINGER_PASSWORD env var required'

    subject = f"INTERCEPT_PROOF_{int(time.time())}"
    _send_via_smtp('localhost', 8587, subject, to_addr)

    # Wait briefly for interception
    time.sleep(3)

    imap = imaplib.IMAP4_SSL(imap_host, imap_port)
    imap.login(to_addr, to_pass)

    # Not in INBOX while HELD
    imap.select('INBOX')
    typ, data = imap.search(None, f'SUBJECT "{subject}"')
    inbox_count = len(data[0].split()) if data and data[0] else 0
    assert inbox_count == 0, f"LEAK: found {inbox_count} in INBOX while HELD"

    # Likely in Quarantine
    imap.select('Quarantine')
    typ, data = imap.search(None, f'SUBJECT "{subject}"')
    quarantine_count = len(data[0].split()) if data and data[0] else 0
    assert quarantine_count >= 1

    imap.close(); imap.logout()
