#!/usr/bin/env python3
"""
Live E2E Interception Test (Gmail-only)

Validates: send via Gmail SMTP -> watcher holds (not in INBOX) -> edit -> release -> edited subject appears in INBOX.

Requirements:
- App running on http://localhost:5000
- Gmail account exists in DB matching .env GMAIL_ADDRESS
- ENABLE_LIVE_EMAIL_TESTS=1 in environment
- python-dotenv and requests installed
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
TIMEOUT_SEND_TO_HELD = int(os.environ.get("E2E_TIMEOUT_HELD", "90"))
TIMEOUT_RELEASE_DELIVER = int(os.environ.get("E2E_TIMEOUT_DELIVER", "90"))


def require_live_gate():
    if str(os.environ.get("ENABLE_LIVE_EMAIL_TESTS", "0")).lower() not in ("1", "true", "yes"):
        raise SystemExit("ENABLE_LIVE_EMAIL_TESTS=1 required to run this script.")


def load_gmail():
    load_dotenv()
    email_addr = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_PASSWORD")
    if not email_addr or not password:
        raise SystemExit("Missing GMAIL_ADDRESS/GMAIL_PASSWORD in .env")
    return {
        "email": email_addr,
        "password": password,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_ssl": False,
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "imap_ssl": True,
    }


def login_admin(session: requests.Session):
    r = session.get(urljoin(BASE_URL, "/login"))
    r.raise_for_status()
    import re
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("CSRF token not found on /login")
    token = m.group(1)
    r2 = session.post(urljoin(BASE_URL, "/login"), data={
        "csrf_token": token,
        "username": "admin",
        "password": "admin123",
    }, allow_redirects=False)
    if r2.status_code not in (302, 303):
        raise RuntimeError(f"Login failed: HTTP {r2.status_code}")


def get_accounts(session: requests.Session):
    r = session.get(urljoin(BASE_URL, "/api/accounts"))
    r.raise_for_status()
    return (r.json() or {}).get("accounts", [])


def find_account_id(accounts, email_addr):
    e = (email_addr or "").lower()
    for a in accounts:
        if (a.get("email_address") or "").lower() == e:
            return a["id"]
    return None


def update_account(session: requests.Session, account_id: int, cfg: dict):
    payload = {
        "imap_username": cfg["email"],
        "imap_password": cfg["password"],
        "smtp_username": cfg["email"],
        "smtp_password": cfg["password"],
        "imap_host": cfg["imap_host"],
        "imap_port": int(cfg["imap_port"]),
        "imap_use_ssl": bool(cfg["imap_ssl"]),
        "smtp_host": cfg["smtp_host"],
        "smtp_port": int(cfg["smtp_port"]),
        "smtp_use_ssl": bool(cfg["smtp_ssl"]),
    }
    # get CSRF token cookie
    r_token = session.get(urljoin(BASE_URL, "/api/accounts"))
    r_token.raise_for_status()
    headers = {"X-CSRFToken": r_token.cookies.get("csrf_token", "")}
    r = session.put(urljoin(BASE_URL, f"/api/accounts/{account_id}"), json=payload, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to update account {account_id}: {r.text}")


def start_watcher(session: requests.Session, account_id: int):
    r = session.post(urljoin(BASE_URL, f"/api/accounts/{account_id}/monitor/start"))
    if r.status_code != 200 or not (r.json().get("success")):
        raise RuntimeError(f"Failed to start watcher for {account_id}: {r.text}")


def send_via_gmail(cfg: dict, to_addr: str, subject: str, body: str) -> str:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["email"]
    msg["To"] = to_addr
    msg["Date"] = formatdate()
    msg_id = make_msgid()
    msg["Message-ID"] = msg_id
    s = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=20)
    s.ehlo(); s.starttls(); s.ehlo()
    s.login(cfg["email"], cfg["password"])
    s.send_message(msg)
    try:
        s.quit()
    except Exception:
        pass
    return msg_id


def imap_search_subject(cfg: dict, folder: str, subject_contains: str) -> bool:
    M = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"]) if cfg["imap_ssl"] else imaplib.IMAP4(cfg["imap_host"], cfg["imap_port"])
    M.login(cfg["email"], cfg["password"])
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
    r = session.get(urljoin(BASE_URL, "/api/interception/held"))
    if r.status_code != 200:
        return None
    items = (r.json() or {}).get("messages", [])
    for it in items:
        subj = (it.get("subject") or "")
        if subject_contains in subj:
            return it.get("id")
    return None


def edit_email(session: requests.Session, email_id: int, new_subject: str, new_body: str):
    r = session.post(urljoin(BASE_URL, f"/api/email/{email_id}/edit"), json={"subject": new_subject, "body_text": new_body})
    if r.status_code != 200 or not (r.json().get("ok") or r.json().get("success")):
        raise RuntimeError(f"Edit failed: {r.text}")


def release_email(session: requests.Session, email_id: int, new_subject: str, new_body: str):
    r = session.post(urljoin(BASE_URL, f"/api/interception/release/{email_id}"), json={"edited_subject": new_subject, "edited_body": new_body})
    if r.status_code != 200 or not r.json().get("ok"):
        raise RuntimeError(f"Release failed: {r.text}")


def main():
    require_live_gate()
    g = load_gmail()
    s = requests.Session()
    login_admin(s)

    # ensure Gmail account present; optionally update creds (watcher uses DB creds)
    accs = get_accounts(s)
    gid = find_account_id(accs, g["email"])
    if not gid:
        raise SystemExit(f"Account for {g['email']} not found in DB. Add it via /accounts first.")

    skip_update = str(os.environ.get("E2E_SKIP_ACCOUNT_UPDATE", "0")).lower() in ("1", "true", "yes")
    if not skip_update:
        update_account(s, gid, g)
        start_watcher(s, gid)
    else:
        print("[INFO] Skipping account update/start per E2E_SKIP_ACCOUNT_UPDATE")

    unique = f"E2E {int(time.time())}"
    subj = f"[E2E-TEST] {unique}"
    body = f"This is a live Gmail E2E test at {time.ctime()}"
    edited_subj = subj + " [EDITED]"
    edited_body = body + "\nEdited body applied by app"

    send_via_gmail(g, g["email"], subj, body)

    # verify not in INBOX (should be held)
    def not_in_inbox():
        return not imap_search_subject(g, "INBOX", subj)
    if not poll_until(not_in_inbox, TIMEOUT_SEND_TO_HELD):
        print("[FAIL] Message still in INBOX after timeout (not held)")
        raise SystemExit(1)

    # optional check in Quarantine (may differ per provider)
    def in_quarantine():
        return imap_search_subject(g, "Quarantine", subj)
    _ = poll_until(in_quarantine, 30)

    # find in local app
    email_id = None
    def have_email_id():
        nonlocal email_id
        email_id = find_held_email_id(s, subj)
        return bool(email_id)
    if not poll_until(have_email_id, 60) or not email_id:
        print("[FAIL] Held email not visible in app DB")
        raise SystemExit(1)

    # edit and release
    edit_email(s, email_id, edited_subj, edited_body)
    release_email(s, email_id, edited_subj, edited_body)

    # verify edited subject appears in INBOX
    def edited_in_inbox():
        return imap_search_subject(g, "INBOX", edited_subj)
    if not poll_until(edited_in_inbox, TIMEOUT_RELEASE_DELIVER):
        print("[FAIL] Edited message not found in INBOX after release")
        raise SystemExit(1)

    print("[PASS] Gmail E2E: held -> edited -> released -> edited subject in INBOX")


if __name__ == "__main__":
    main()
