#!/usr/bin/env python3
"""
IMAP Connection Diagnostic Tool

This script helps diagnose IMAP connection issues by:
1. Reading account credentials from the database
2. Attempting connection with detailed error reporting
3. Validating credentials and configuration
4. Providing actionable troubleshooting steps

Usage:
    python scripts/diagnose_imap.py [account_id]

If no account_id is provided, all active accounts will be tested.
"""

import sys
import os
import sqlite3
import ssl as sslmod
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.imap_watcher import AccountConfig, ImapWatcher
from app.utils.crypto import decrypt_credential
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
log = logging.getLogger(__name__)


def get_account_from_db(account_id: int) -> dict:
    """Fetch account details from database."""
    db_path = os.getenv('DB_PATH', 'email_manager.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute(
        """SELECT id, account_name, email_address, imap_host, imap_port,
                  imap_username, imap_password, imap_use_ssl, is_active,
                  last_error, last_checked
           FROM email_accounts WHERE id=?""",
        (account_id,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return dict(row)


def get_all_active_accounts() -> list:
    """Fetch all active account IDs."""
    db_path = os.getenv('DB_PATH', 'email_manager.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    rows = cur.execute(
        "SELECT id FROM email_accounts WHERE is_active=1 ORDER BY id"
    ).fetchall()

    conn.close()

    return [row[0] for row in rows]


def diagnose_account(account_id: int):
    """Run diagnostic tests on a specific account."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING ACCOUNT {account_id}")
    print(f"{'='*80}\n")

    # Fetch account details
    account = get_account_from_db(account_id)
    if not account:
        print(f"❌ ERROR: Account {account_id} not found in database")
        return False

    print(f"Account Name: {account['account_name']}")
    print(f"Email Address: {account['email_address']}")
    print(f"IMAP Host: {account['imap_host']}:{account['imap_port']}")
    print(f"IMAP Username: {account['imap_username']}")
    print(f"Use SSL: {bool(account['imap_use_ssl'])}")
    print(f"Is Active: {bool(account['is_active'])}")
    print(f"Last Error: {account['last_error'] or 'None'}")
    print(f"Last Checked: {account['last_checked'] or 'Never'}")
    print()

    # Check if account is active
    if not account['is_active']:
        print("⚠️  WARNING: Account is marked as inactive (is_active=0)")
        print("   This usually means the circuit breaker was tripped due to repeated failures.")
        print("   Action: Fix credentials, then re-activate via dashboard or database update")
        return False

    # Validate required fields
    errors = []
    if not account['imap_host']:
        errors.append("Missing IMAP host")
    if not account['imap_username']:
        errors.append("Missing IMAP username")
    if not account['imap_password']:
        errors.append("Missing IMAP password")

    if errors:
        print("❌ CONFIGURATION ERRORS:")
        for error in errors:
            print(f"   - {error}")
        return False

    # Decrypt password
    try:
        password = decrypt_credential(account['imap_password'])
        if password:
            print("✓ Password successfully decrypted from database")
        else:
            print("❌ ERROR: Password decryption returned None/empty")
            print("   This indicates a problem with the encryption key or corrupted data")
            return False
    except Exception as e:
        print(f"❌ ERROR: Failed to decrypt password: {e}")
        print("   This indicates a problem with the encryption key or corrupted data")
        return False

    # Validate password is not empty
    if not password:
        print("❌ ERROR: Decrypted password is empty")
        return False

    print(f"✓ Password length: {len(password)} characters (masked for security)")
    print()

    # Create AccountConfig
    cfg = AccountConfig(
        imap_host=account['imap_host'],
        imap_port=account['imap_port'],
        username=account['imap_username'],
        password=password,
        use_ssl=bool(account['imap_use_ssl']),
        account_id=account_id
    )

    # Attempt connection
    print("Testing IMAP connection...")
    print("-" * 80)

    watcher = ImapWatcher(cfg)
    client = watcher._connect()

    if client is None:
        print("\n❌ CONNECTION FAILED")
        print("\nTROUBLESHOOTING STEPS:")

        # Provide specific guidance based on last error
        last_error = account['last_error'] or ""
        error_lower = last_error.lower()

        if 'auth' in error_lower or 'login' in error_lower:
            print("\n🔐 AUTHENTICATION FAILURE DETECTED")
            print("   1. For Gmail/Outlook: Generate and use an App Password")
            print("      - Gmail: https://myaccount.google.com/apppasswords")
            print("      - Outlook: https://account.live.com/proofs/AppPassword")
            print("   2. Verify username is the full email address")
            print("   3. Check if account has 2FA enabled (required for app passwords)")
            print("   4. Ensure IMAP is enabled in email provider settings")

        elif 'ssl' in error_lower or 'tls' in error_lower:
            print("\n🔒 SSL/TLS ERROR DETECTED")
            print("   1. Verify SSL port is correct:")
            print("      - SSL: port 993 (most common)")
            print("      - STARTTLS: port 143")
            print("   2. Check if provider requires specific SSL settings")
            print("   3. Try toggling the 'Use SSL' setting")

        elif 'timeout' in error_lower:
            print("\n⏱️  CONNECTION TIMEOUT DETECTED")
            print("   1. Check firewall settings allow outbound IMAP connections")
            print("   2. Verify IMAP host is correct and reachable")
            print("   3. Try increasing timeout in .env: EMAIL_CONN_TIMEOUT=30")
            print("   4. Check if VPN or proxy is interfering")

        elif 'refused' in error_lower:
            print("\n🚫 CONNECTION REFUSED")
            print("   1. Verify IMAP host and port are correct")
            print("   2. Check if IMAP service is enabled by provider")
            print("   3. Confirm no firewall blocking the connection")

        else:
            print("\n❓ UNKNOWN ERROR")
            print("   1. Check application logs for detailed error messages")
            print("   2. Verify all account settings are correct")
            print("   3. Try testing with a different email client (e.g., Thunderbird)")

        print("\n📝 Database Update Commands:")
        print(f"   -- To reactivate after fixing credentials:")
        print(f"   UPDATE email_accounts SET is_active=1, last_error=NULL WHERE id={account_id};")

        return False

    print("\n✅ CONNECTION SUCCESSFUL!")
    print(f"   - Logged in as: {account['imap_username']}")
    print(f"   - Server capabilities: {client.capabilities()}")

    # Test folder access
    try:
        client.select_folder('INBOX', readonly=True)
        print("   - INBOX access: ✓")
    except Exception as e:
        print(f"   - INBOX access: ❌ ({e})")

    # Check for IDLE support
    caps = client.capabilities() or []
    has_idle = b"IDLE" in caps
    has_move = b"MOVE" in caps or b"UIDPLUS" in caps

    print(f"   - IDLE support: {'✓' if has_idle else '❌'}")
    print(f"   - MOVE/UIDPLUS support: {'✓' if has_move else '❌'}")

    # Cleanup
    try:
        client.logout()
    except Exception:
        pass

    print("\n✅ ALL TESTS PASSED - Account is properly configured")
    return True


def main():
    """Main diagnostic function."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     IMAP Connection Diagnostic Tool                          ║
║                     Email Management Tool v2.8                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Parse account ID from command line
    if len(sys.argv) > 1:
        try:
            account_id = int(sys.argv[1])
            accounts = [account_id]
        except ValueError:
            print(f"ERROR: Invalid account ID: {sys.argv[1]}")
            print("Usage: python scripts/diagnose_imap.py [account_id]")
            sys.exit(1)
    else:
        # Test all active accounts
        accounts = get_all_active_accounts()
        if not accounts:
            print("No active accounts found in database")
            print("\nTo add an account, use the web dashboard at http://localhost:5000/accounts")
            sys.exit(0)

        print(f"Found {len(accounts)} active account(s): {accounts}")
        print("Testing all accounts...\n")

    # Run diagnostics
    results = {}
    for account_id in accounts:
        success = diagnose_account(account_id)
        results[account_id] = success

    # Summary
    if len(accounts) > 1:
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}\n")

        for account_id, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  Account {account_id}: {status}")

        passed = sum(1 for s in results.values() if s)
        print(f"\n{passed}/{len(accounts)} accounts passed diagnostics")

    # Exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
