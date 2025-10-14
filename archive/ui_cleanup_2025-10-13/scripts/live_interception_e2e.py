#!/usr/bin/env python3
"""
Live E2E Interception Test (REAL SMTP + IMAP)

This script validates the full live flow for two accounts (Gmail <-> Hostinger):
1) Send an email via the PROVIDER SMTP (not local proxy)
2) IMAP watcher intercepts and moves to Quarantine (not visible in INBOX)
3) Edit the held message via local app API, then release
4) Verify the edited message appears in the remote INBOX with edited subject/body

Requirements:
- App running on http://localhost:5000 and logged-in endpoints available
- Accounts exist in DB and match the two emails in .env (or script will update them)
- ENABLE_LIVE_EMAIL_TESTS=1 in environment (safety gate)
- python-dotenv installed; requests installed (pip install requests)

Usage:
  python scripts/live_interception_e2e.py

Notes:
- No secrets are printed. Uses .env (GMAIL_* and HOSTINGER_*) and admin/admin123.
- This test exercises BOTH directions: Gmail -> Hostinger and Hostinger -> Gmail.
"""
import os
import time
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from urllib.parse import urljoin

try:
    import requests
except Exception:
    raise SystemExit("requests is required. Install with: pip install requests")

try:
    from dotenv import load_dotenv
except Exception:
    raise SystemExit("python-dotenv is required. Install with: pip install python-dotenv")


BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000/")
TIMEOUT_SEND_TO_HELD = int(os.environ.get("E2E_TIMEOUT_HELD", "90"))
TIMEOUT_RELEASE_DELIVER = int(os.environ.get("E2E_TIMEOUT_DELIVER", "90"))


def require_live_gate():
    if str(os.environ.get("ENABLE_LIVE_EMAIL_TESTS", "0")).lower() not in ("1", "true", "yes"):
        raise SystemExit("ENABLE_LIVE_EMAIL_TESTS=1 required to run this script.")


def load_env():
    load_dotenv()
    cfg = {
        'gmail': {
            'email': os.environ.get('GMAIL_ADDRESS'),
            'password': os.environ.get('GMAIL_PASSWORD'),
            'smtp_host': 'smtp.gmail.com', 'smtp_port': 587, 'smtp_ssl': False,
            'imap_host': 'imap.gmail.com', 'imap_port': 993, 'imap_ssl': True,
        },
        'hostinger': {
            'email': os.environ.get('HOSTINGER_ADDRESS'),
            'password': os.environ.get('HOSTINGER_PASSWORD'),
            'smtp_host': 'smtp.hostinger.com', 'smtp_port': 465, 'smtp_ssl': True,
            'imap_host': 'imap.hostinger.com', 'imap_port': 993, 'imap_ssl': True,
        },
    }
    for name, c in cfg.items():
        if not c['email'] or not c['password']:
            raise SystemExit(f"Missing credentials in .env for {name}")
    return cfg


def login_admin(session: requests.Session):
    r = session.get(urljoin(BASE_URL, '/login'))
    r.raise_for_status()
    import re
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("CSRF token not found on /login")
    token = m.group(1)
    r2 = session.post(urljoin(BASE_URL, '/login'), data={
        'csrf_token': token,
        'username': 'admin', 'password': 'admin123'
    }, allow_redirects=False)
    if r2.status_code not in (302, 303):
        raise RuntimeError(f"Login failed: HTTP {r2.status_code}")


def get_accounts(session: requests.Session):
    r = session.get(urljoin(BASE_URL, '/api/accounts'))
    r.raise_for_status()
    data = r.json()
    return data.get('accounts', [])


def find_account_id(accounts, email_addr):
    email_l = (email_addr or '').lower()
    for a in accounts:
        if (a.get('email_address') or '').lower() == email_l:
            return a['id']
    return None


def update_account_creds(session: requests.Session, account_id: int, imap_user: str, imap_pwd: str, smtp_user: str, smtp_pwd: str, imap_host: str, imap_port: int, smtp_host: str, smtp_port: int, imap_ssl: bool, smtp_ssl: bool):
    payload = {
        'imap_username': imap_user,
        'imap_password': imap_pwd,
        'smtp_username': smtp_user,
        'smtp_password': smtp_pwd,
        'imap_host': imap_host, 'imap_port': int(imap_port), 'imap_use_ssl': bool(imap_ssl),
        'smtp_host': smtp_host, 'smtp_port': int(smtp_port), 'smtp_use_ssl': bool(smtp_ssl),
    }

    # Get CSRF token for API requests
    r_token = session.get(urljoin(BASE_URL, '/api/accounts'))
    r_token.raise_for_status()

    # Add CSRF token to headers
    headers = {
        'X-CSRFToken': r_token.cookies.get('csrf_token', '')
    }

    r = session.put(urljoin(BASE_URL, f'/api/accounts/{account_id}'), json=payload, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to update account {account_id}: {r.text}")


def start_watcher(session: requests.Session, account_id: int):
    r = session.post(urljoin(BASE_URL, f'/api/accounts/{account_id}/monitor/start'))
    if r.status_code != 200 or not r.json().get('success'):
        raise RuntimeError(f"Failed to start watcher for {account_id}: {r.text}")


def stop_watcher(session: requests.Session, account_id: int):
    session.post(urljoin(BASE_URL, f'/api/accounts/{account_id}/monitor/stop'))


def send_via_provider(smtp_host: str, smtp_port: int, use_ssl: bool, username: str, password: str, from_addr: str, to_addr: str, subject: str, body: str) -> str:
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Date'] = formatdate()
    msg_id = make_msgid()
    msg['Message-ID'] = msg_id
    if use_ssl or smtp_port == 465:
        s = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
    else:
        s = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
        s.ehlo(); s.starttls(); s.ehlo()
    s.login(username, password)
    s.send_message(msg)
    try:
        s.quit()
    except Exception:
        pass
    return msg_id


def imap_search_subject(host: str, port: int, use_ssl: bool, username: str, password: str, folder: str, subject_contains: str) -> bool:
    if use_ssl or port == 993:
        M = imaplib.IMAP4_SSL(host, port)
    else:
        M = imaplib.IMAP4(host, port)
    M.login(username, password)
    M.select(folder)
    typ, data = M.search(None, '(HEADER Subject "%s")' % subject_contains.replace('"', ''))
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


def find_held_email_id(session: requests.Session, subject_contains: str):
    r = session.get(urljoin(BASE_URL, '/api/interception/held'))
    if r.status_code != 200:
        return None
    items = (r.json() or {}).get('messages', [])
    for it in items:
        subj = (it.get('subject') or '')
        if subject_contains in subj:
            return it.get('id')
    return None


def edit_email(session: requests.Session, email_id: int, new_subject: str, new_body: str):
    r = session.post(urljoin(BASE_URL, f'/api/email/{email_id}/edit'), json={'subject': new_subject, 'body_text': new_body})
    if r.status_code != 200 or not (r.json().get('ok') or r.json().get('success')):
        raise RuntimeError(f"Edit failed: {r.text}")


def release_email(session: requests.Session, email_id: int, new_subject: str, new_body: str):
    r = session.post(urljoin(BASE_URL, f'/api/interception/release/{email_id}'), json={'edited_subject': new_subject, 'edited_body': new_body})
    if r.status_code != 200 or not r.json().get('ok'):
        raise RuntimeError(f"Release failed: {r.text}")


def run_flow(session: requests.Session, sender_cfg: dict, recipient_cfg: dict, accounts_map: dict) -> bool:
    from_addr = sender_cfg['email']; to_addr = recipient_cfg['email']
    unique = f"E2E {int(time.time())}"
    subj = f"[E2E-TEST] {unique}"
    body = f"This is a live E2E test sent at {time.ctime()}"
    edited_subj = subj + " [EDITED]"
    edited_body = body + "\nEdited body applied by app"

    # Ensure watcher started on recipient
    rec_id = accounts_map[to_addr]
    start_watcher(session, rec_id)

    # Send via provider
    msg_id = send_via_provider(
        sender_cfg['smtp_host'], sender_cfg['smtp_port'], sender_cfg['smtp_ssl'],
        sender_cfg['email'], sender_cfg['password'], from_addr, to_addr, subj, body
    )
    print(f"[SEND] {from_addr} -> {to_addr} msg_id={msg_id}")

    # Confirm NOT in INBOX (should be moved to Quarantine shortly)
    def not_in_inbox():
        return not imap_search_subject(recipient_cfg['imap_host'], recipient_cfg['imap_port'], recipient_cfg['imap_ssl'], recipient_cfg['email'], recipient_cfg['password'], 'INBOX', subj)
    ok_not_in_inbox = poll_until(not_in_inbox, TIMEOUT_SEND_TO_HELD)
    if not ok_not_in_inbox:
        print("[FAIL] Message still in INBOX after timeout (was not held)")
        return False

    # Confirm in Quarantine
    def in_quarantine():
        return imap_search_subject(recipient_cfg['imap_host'], recipient_cfg['imap_port'], recipient_cfg['imap_ssl'], recipient_cfg['email'], recipient_cfg['password'], 'Quarantine', subj)
    ok_quarantine = poll_until(in_quarantine, 30)
    if not ok_quarantine:
        print("[WARN] Message not found in Quarantine (server may not expose or folder differs)")

    # Get email_id from local app
    def find_email_id():
        eid = find_held_email_id(session, subj)
        return eid
    email_id = None
    def have_email_id():
        nonlocal email_id
        email_id = find_email_id()
        return bool(email_id)
    ok_db = poll_until(have_email_id, 60)
    if not ok_db or not email_id:
        print("[FAIL] Held email not visible in app DB")
        return False
    print(f"[HELD] email_id={email_id}")

    # Edit and release
    edit_email(session, email_id, edited_subj, edited_body)
    release_email(session, email_id, edited_subj, edited_body)
    print("[RELEASED]")

    # Confirm edited subject appears in INBOX
    def edited_in_inbox():
        return imap_search_subject(recipient_cfg['imap_host'], recipient_cfg['imap_port'], recipient_cfg['imap_ssl'], recipient_cfg['email'], recipient_cfg['password'], 'INBOX', edited_subj)
    ok_delivered = poll_until(edited_in_inbox, TIMEOUT_RELEASE_DELIVER)
    if not ok_delivered:
        print("[FAIL] Edited message not found in INBOX after release")
        return False
    print("[PASS] Flow verified: held (not in inbox) -> edited -> released -> in inbox")
    return True


def main():
    require_live_gate()
    cfg = load_env()
    s = requests.Session()
    login_admin(s)

    # Ensure accounts present and update IMAP/SMTP creds to match .env (so watchers can auth)
    accs = get_accounts(s)
    id_map = {}
    for name in ('gmail', 'hostinger'):
        aid = find_account_id(accs, cfg[name]['email'])
        if not aid:
            raise SystemExit(f"Account for {cfg[name]['email']} not found in DB. Add it via /accounts first.")
        id_map[cfg[name]['email']] = aid
        # Update creds to ensure watchers can log in
        update_account_creds(
            s, aid,
            imap_user=cfg[name]['email'], imap_pwd=cfg[name]['password'],
            smtp_user=cfg[name]['email'], smtp_pwd=cfg[name]['password'],
            imap_host=cfg[name]['imap_host'], imap_port=cfg[name]['imap_port'], imap_ssl=cfg[name]['imap_ssl'],
            smtp_host=cfg[name]['smtp_host'], smtp_port=cfg[name]['smtp_port'], smtp_ssl=cfg[name]['smtp_ssl'],
        )

    # Run both directions
    ok1 = run_flow(s, cfg['gmail'], cfg['hostinger'], id_map)
    ok2 = run_flow(s, cfg['hostinger'], cfg['gmail'], id_map)

    print("\n=== Summary ===")
    print(f"Gmail -> Hostinger: {'PASS' if ok1 else 'FAIL'}")
    print(f"Hostinger -> Gmail: {'PASS' if ok2 else 'FAIL'}")
    if ok1 and ok2:
        print("E2E: PASS")
        raise SystemExit(0)
    else:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
