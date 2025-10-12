"""
Live credential smoke test for Email Management Tool.

- Validates .env has required variables
- Tests IMAP (SSL) and SMTP (SSL/STARTTLS per provider) logins for Gmail and Hostinger
- Exits non‑zero if any mandatory check fails

Usage:
  python -m pip install -r requirements.txt  # ensure imapclient present
  python scripts/live_check.py
"""
from __future__ import annotations

import os
import ssl
import sys
import smtplib
from contextlib import contextmanager

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from imapclient import IMAPClient
except Exception as e:
    print(f"ERROR: imapclient not available: {e}")
    sys.exit(2)

# Load .env if available
if load_dotenv:
    load_dotenv()

# Required env vars
REQUIRED = [
    "GMAIL_ADDRESS",
    "GMAIL_PASSWORD",
    "HOSTINGER_ADDRESS",
    "HOSTINGER_PASSWORD",
]
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    print("ERROR: Missing required .env variables:", ", ".join(missing))
    print("Populate .env with live credentials before running live checks.")
    sys.exit(2)

GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"].strip()
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"].strip()
HOSTINGER_ADDRESS = os.environ["HOSTINGER_ADDRESS"].strip()
HOSTINGER_PASSWORD = os.environ["HOSTINGER_PASSWORD"].strip()


def test_imap(host: str, port: int, user: str, password: str) -> tuple[bool, str]:
    try:
        with IMAPClient(host, port=port, ssl=True, ssl_context=ssl.create_default_context()) as client:
            client.login(user, password)
            client.select_folder("INBOX", readonly=True)
            client.logout()
        return True, "IMAP OK"
    except Exception as e:
        return False, f"IMAP FAIL: {e}"


def test_smtp_ssl(host: str, port: int, user: str, password: str) -> tuple[bool, str]:
    try:
        with smtplib.SMTP_SSL(host=host, port=port, context=ssl.create_default_context(), timeout=20) as s:
            s.login(user, password)
        return True, "SMTP SSL OK"
    except Exception as e:
        return False, f"SMTP SSL FAIL: {e}"


def test_smtp_starttls(host: str, port: int, user: str, password: str) -> tuple[bool, str]:
    try:
        with smtplib.SMTP(host=host, port=port, timeout=20) as s:
            s.ehlo()
            s.starttls(context=ssl.create_default_context())
            s.ehlo()
            s.login(user, password)
        return True, "SMTP STARTTLS OK"
    except Exception as e:
        return False, f"SMTP STARTTLS FAIL: {e}"


def check_gmail() -> list[str]:
    results: list[str] = []
    ok, msg = test_imap("imap.gmail.com", 993, GMAIL_ADDRESS, GMAIL_PASSWORD)
    results.append(f"GMAIL {msg}")
    gok, gmsg = test_smtp_starttls("smtp.gmail.com", 587, GMAIL_ADDRESS, GMAIL_PASSWORD)
    results.append(f"GMAIL {gmsg}")
    return results if ok and gok else results + ["GMAIL CHECK: FAIL"]


def check_hostinger() -> list[str]:
    results: list[str] = []
    ok, msg = test_imap("imap.hostinger.com", 993, HOSTINGER_ADDRESS, HOSTINGER_PASSWORD)
    results.append(f"HOSTINGER {msg}")
    hok, hmsg = test_smtp_ssl("smtp.hostinger.com", 465, HOSTINGER_ADDRESS, HOSTINGER_PASSWORD)
    results.append(f"HOSTINGER {hmsg}")
    return results if ok and hok else results + ["HOSTINGER CHECK: FAIL"]


def main() -> int:
    lines: list[str] = []
    lines.extend(check_gmail())
    lines.extend(check_hostinger())

    failed = any("FAIL" in l for l in lines)
    print("\n".join(lines))
    if failed:
        print("\nOne or more live checks failed. Verify App Passwords, ports, and IMAP enabled.")
        return 1
    print("\nAll live checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
