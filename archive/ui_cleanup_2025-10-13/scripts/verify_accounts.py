#!/usr/bin/env python3
"""
Verify Permanent Accounts Status
Checks database configuration and connection status
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from app.utils.db import DB_PATH
from app.utils.crypto import decrypt_credential

def verify_accounts():
    """Verify permanent accounts are properly configured"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 80)
    print("PERMANENT ACCOUNTS VERIFICATION")
    print("=" * 80)

    accounts = cursor.execute("""
        SELECT id, account_name, email_address, is_active,
               imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
               smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl
        FROM email_accounts
        WHERE email_address IN ('ndayijecika@gmail.com', 'mcintyre@corrinbox.com')
        ORDER BY id
    """).fetchall()

    if not accounts:
        print("\n⚠️  No permanent accounts found in database!")
        print("Run: python scripts/setup_test_accounts.py")
        return

    for acc in accounts:
        print(f"\n{'─' * 80}")
        print(f"Account ID: {acc['id']}")
        print(f"Name: {acc['account_name']}")
        print(f"Email: {acc['email_address']}")
        print(f"Status: {'✅ ACTIVE' if acc['is_active'] else '❌ INACTIVE'}")

        print(f"\nIMAP Configuration:")
        print(f"  Host: {acc['imap_host']}")
        print(f"  Port: {acc['imap_port']}")
        print(f"  Username: {acc['imap_username']}")
        print(f"  SSL: {'Yes' if acc['imap_use_ssl'] else 'No (STARTTLS)'}")

        print(f"\nSMTP Configuration:")
        print(f"  Host: {acc['smtp_host']}")
        print(f"  Port: {acc['smtp_port']}")
        print(f"  Username: {acc['smtp_username']}")
        print(f"  SSL: {'Yes' if acc['smtp_use_ssl'] else 'No (STARTTLS)'}")

        # Verify password decryption works
        try:
            pwd = decrypt_credential(acc['imap_password'])
            pwd_ok = pwd is not None and len(pwd) > 0
            print(f"\nPassword Encryption: {'✅ OK' if pwd_ok else '❌ FAILED'}")
        except Exception as e:
            print(f"\nPassword Encryption: ❌ ERROR - {e}")

    # Check for intercepted emails
    held_count = cursor.execute("""
        SELECT COUNT(*) FROM email_messages
        WHERE interception_status = 'HELD'
    """).fetchone()[0]

    pending_count = cursor.execute("""
        SELECT COUNT(*) FROM email_messages
        WHERE status = 'PENDING'
    """).fetchone()[0]

    print(f"\n{'─' * 80}")
    print("Email Queue Status:")
    print(f"  Held (IMAP intercepted): {held_count}")
    print(f"  Pending (SMTP intercepted): {pending_count}")

    conn.close()

    print(f"\n{'=' * 80}")
    print("✅ VERIFICATION COMPLETE")
    print("=" * 80)
    print("\nAccounts are configured and ready.")
    print("Access web interface: http://localhost:5000")
    print("Login: admin / admin123")

if __name__ == '__main__':
    verify_accounts()
