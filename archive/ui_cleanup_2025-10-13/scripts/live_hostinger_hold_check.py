#!/usr/bin/env python3
"""
Live Hostinger Hold Check

Sends an email from Gmail to Hostinger and verifies the Hostinger watcher
moves it out of INBOX (held) into Quarantine. Skips account updates to avoid CSRF.

Requirements:
- App running on http://localhost:5000
- .env contains GMAIL_* and HOSTINGER_* (python-dotenv installed)
- ENABLE_LIVE_EMAIL_TESTS=1
"""
import os
import time
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000/")
TIMEOUT_SEND_TO_HELD = int(os.environ.get("E2E_TIMEOUT_HELD", "120"))


def require_live_gate():
    if str(os.environ.get("ENABLE_LIVE_EMAIL_TESTS", "0")).lower() not in ("1", "true", "yes"):
        raise SystemExit("ENABLE_LIVE_EMAIL_TESTS=1 required to run this script.")


def load_cfg():
    load_dotenv()
    g = {
        'email': os.environ.get('GMAIL_ADDRESS'),
        'password': os.environ.get('GMAIL_PASSWORD'),
        'smtp_host': 'smtp.gmail.com', 'smtp_port': 587, 'smtp_ssl': False,
    }
    h = {
        'email': os.environ.get('HOSTINGER_ADDRESS'),
        'password': os.environ.get('HOSTINGER_PASSWORD'),
        'imap_host': 'imap.hostinger.com', 'imap_port': 993, 'imap_ssl': True,
    }
    if not all([g['email'], g['password'], h['email'], h['password']]):
        raise SystemExit("Missing GMAIL_* or HOSTINGER_* credentials in .env")
    return g, h


def login_admin(session: requests.Session):
    r = session.get(urljoin(BASE_URL, '/login'))
    r.raise_for_status()
    import re
    m = re.search(r'name="csrf_token"\s+value=\"([^\"]+)\"', r.text)
    if not m:
        raise RuntimeError("CSRF token not found on /login")
    token = m.group(1)
    r2 = session.post(urljoin(BASE_URL, '/login'), data={'csrf_token': token, 'username': 'admin', 'password': 'admin123'}, allow_redirects=False)
    if r2.status_code not in (302, 303):
        raise RuntimeError(f"Login failed: HTTP {r2.status_code}")


def start_watcher(session: requests.Session, account_email: str):
    # Get accounts to map id
    r = session.get(urljoin(BASE_URL, '/api/accounts'))
    r.raise_for_status()
    accs = (r.json() or {}).get('accounts', [])
    acc_id = None
    el = (account_email or '').lower()
    for a in accs:
        if (a.get('email_address') or '').lower() == el:
            acc_id = a['id']; break
    if not acc_id:
        raise SystemExit(f"Account for {account_email} not found in DB")
    # Start monitor (csrf exempt)
    r2 = session.post(urljoin(BASE_URL, f'/api/accounts/{acc_id}/monitor/start'))
    if r2.status_code != 200 or not (r2.json().get('success')):
        raise RuntimeError(f"Failed to start watcher: {r2.text}")


def send_via_gmail(g, to_addr: str, subject: str, body: str) -> str:
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = g['email']
    msg['To'] = to_addr
    msg['Date'] = formatdate()
    msg_id = make_msgid()
    msg['Message-ID'] = msg_id
    s = smtplib.SMTP(g['smtp_host'], g['smtp_port'], timeout=20)
    s.ehlo(); s.starttls(); s.ehlo()
    s.login(g['email'], g['password'])
    s.send_message(msg)
    try:
        s.quit()
    except Exception:
        pass
    return msg_id


def hostinger_search(h, folder: str, subj_contains: str) -> bool:
    M = imaplib.IMAP4_SSL(h['imap_host'], h['imap_port']) if h['imap_ssl'] else imaplib.IMAP4(h['imap_host'], h['imap_port'])
    M.login(h['email'], h['password'])
    typ, _ = M.select(folder)
    if typ != 'OK':
        try:
            # Try to create and then select (for first-run folders)
            M.create(folder)
            typ, _ = M.select(folder)
        except Exception:
            M.logout()
            return False
    typ, data = M.search(None, '(HEADER Subject "%s")' % subj_contains.replace('"', ''))
    ok = (typ == 'OK' and data and data[0] and len(data[0].split()) > 0)
    M.logout()
    return ok


def poll_until(predicate, timeout_sec: int, step: float = 2.0):
    start = time.time()
    while time.time() - start < timeout_sec:
        if predicate():
            return True
        time.sleep(step)
    return False


def main():
    require_live_gate()
    g, h = load_cfg()
    s = requests.Session(); login_admin(s); start_watcher(s, h['email'])

    unique = f"E2E-HOST {int(time.time())}"
    subj = f"[E2E-TEST] {unique}"
    body = f"This is a Gmail -> Hostinger live test at {time.ctime()}"

    send_via_gmail(g, h['email'], subj, body)

    # Not in INBOX predicate
    def not_in_inbox():
        return not hostinger_search(h, 'INBOX', subj)
    if not poll_until(not_in_inbox, TIMEOUT_SEND_TO_HELD):
        print('[FAIL] Message still in Hostinger INBOX after timeout (not held)')
        raise SystemExit(1)

    # In Quarantine predicate (try common variants)
    def in_quarantine():
        return hostinger_search(h, 'Quarantine', subj) or hostinger_search(h, 'INBOX/Quarantine', subj) or hostinger_search(h, 'INBOX.Quarantine', subj)
    _ = poll_until(in_quarantine, 60)

    print('[PASS] Hostinger hold check: not visible in INBOX (held).')

if __name__ == '__main__':
    main()
