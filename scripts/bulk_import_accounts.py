#!/usr/bin/env python3
"""
Bulk import email accounts from a CSV file.

Columns supported (headers are case-insensitive):
  - account_name (optional)
  - email_address (required)
  - imap_username (default: email_address)
  - imap_password (required)
  - imap_host, imap_port, imap_use_ssl (optional)
  - smtp_username (default: email_address)
  - smtp_password (required)
  - smtp_host, smtp_port, smtp_use_ssl (optional)
  - is_active (default: 1)

If host/port/use_ssl fields are missing and --auto-detect is provided, settings
are auto-detected from the email domain.

Usage:
  python scripts/bulk_import_accounts.py accounts.csv --auto-detect [--dry-run]
"""
import argparse
import csv
import os
import sqlite3
from typing import Dict, Any

from dotenv import load_dotenv

# Ensure app modules are importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
import sys
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.utils.db import DB_PATH
from app.utils.crypto import encrypt_credential
from app.utils.email_helpers import detect_email_settings


def to_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def to_bool(v, default=None):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ('1', 'true', 'yes', 'y'): return True
    if s in ('0', 'false', 'no', 'n'): return False
    return default


def normalize_row(row: Dict[str, Any], auto_detect: bool) -> Dict[str, Any]:
    # lower-case keys for robustness
    r = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
    email = r.get('email_address') or r.get('email')
    if not email:
        raise ValueError('email_address is required')
    account_name = r.get('account_name') or email
    imap_user = r.get('imap_username') or email
    smtp_user = r.get('smtp_username') or email
    imap_pwd = r.get('imap_password')
    smtp_pwd = r.get('smtp_password')
    if not imap_pwd or not smtp_pwd:
        raise ValueError('imap_password and smtp_password are required')

    imap_host = r.get('imap_host'); smtp_host = r.get('smtp_host')
    imap_port = to_int(r.get('imap_port'), 993); smtp_port = to_int(r.get('smtp_port'), 465)
    imap_ssl = to_bool(r.get('imap_use_ssl'), True); smtp_ssl = to_bool(r.get('smtp_use_ssl'), True)

    if auto_detect and (not imap_host or not smtp_host):
        auto = detect_email_settings(email)
        imap_host = imap_host or auto['imap_host']
        imap_port = imap_port or auto['imap_port']
        imap_ssl = auto['imap_use_ssl'] if imap_ssl is None else imap_ssl
        smtp_host = smtp_host or auto['smtp_host']
        smtp_port = smtp_port or auto['smtp_port']
        smtp_ssl = auto['smtp_use_ssl'] if smtp_ssl is None else smtp_ssl

    is_active = 1 if to_bool(r.get('is_active'), True) else 0

    return {
        'account_name': account_name,
        'email_address': email,
        'imap_host': imap_host,
        'imap_port': imap_port,
        'imap_username': imap_user,
        'imap_password': imap_pwd,
        'imap_use_ssl': 1 if (imap_ssl is not False) else 0,
        'smtp_host': smtp_host,
        'smtp_port': smtp_port,
        'smtp_username': smtp_user,
        'smtp_password': smtp_pwd,
        'smtp_use_ssl': 1 if (smtp_ssl is not False) else 0,
        'is_active': is_active,
    }


def upsert_account(conn: sqlite3.Connection, data: Dict[str, Any]) -> str:
    cur = conn.cursor()
    existing = cur.execute("SELECT id FROM email_accounts WHERE email_address=?", (data['email_address'],)).fetchone()
    enc_imap = encrypt_credential(data['imap_password'])
    enc_smtp = encrypt_credential(data['smtp_password'])
    if existing:
        cur.execute(
            """
            UPDATE email_accounts
            SET account_name=?,
                imap_host=?, imap_port=?, imap_username=?, imap_password=?, imap_use_ssl=?,
                smtp_host=?, smtp_port=?, smtp_username=?, smtp_password=?, smtp_use_ssl=?,
                is_active=?, updated_at=CURRENT_TIMESTAMP
            WHERE email_address=?
            """,
            (
                data['account_name'],
                data['imap_host'], data['imap_port'], data['imap_username'], enc_imap, data['imap_use_ssl'],
                data['smtp_host'], data['smtp_port'], data['smtp_username'], enc_smtp, data['smtp_use_ssl'],
                data['is_active'], data['email_address']
            )
        )
        return 'updated'
    else:
        cur.execute(
            """
            INSERT INTO email_accounts (
                account_name, email_address,
                imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
                smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data['account_name'], data['email_address'],
                data['imap_host'], data['imap_port'], data['imap_username'], enc_imap, data['imap_use_ssl'],
                data['smtp_host'], data['smtp_port'], data['smtp_username'], enc_smtp, data['smtp_use_ssl'],
                data['is_active']
            )
        )
        return 'inserted'


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Bulk import email accounts from CSV')
    parser.add_argument('csv_path', help='Path to CSV file')
    parser.add_argument('--auto-detect', action='store_true', help='Auto-detect host/ports for missing values')
    parser.add_argument('--dry-run', action='store_true', help='Parse and validate only; do not write DB')
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"File not found: {args.csv_path}")
        return 2

    with open(args.csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    inserted = updated = skipped = errors = 0
    conn = sqlite3.connect(DB_PATH)
    try:
        for i, row in enumerate(rows, 1):
            try:
                data = normalize_row(row, args.auto_detect)
                if args.dry_run:
                    skipped += 1
                    continue
                res = upsert_account(conn, data)
                if res == 'inserted':
                    inserted += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                print(f"Row {i}: ERROR - {e}")
        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()

    print(f"Done. inserted={inserted} updated={updated} skipped={skipped} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
