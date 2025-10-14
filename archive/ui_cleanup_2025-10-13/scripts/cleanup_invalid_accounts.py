"""
Cleanup Script for Invalid Email Accounts
Removes accounts with corrupt/missing encrypted passwords that cannot be decrypted.

Usage:
    python scripts/cleanup_invalid_accounts.py [--dry-run] [--id ID]

Options:
    --dry-run    Show what would be deleted without actually deleting
    --id ID      Only check/delete specific account ID (default: check all)

Example:
    python scripts/cleanup_invalid_accounts.py --dry-run          # Preview all invalid accounts
    python scripts/cleanup_invalid_accounts.py --id 4            # Delete account ID=4 only
    python scripts/cleanup_invalid_accounts.py                   # Delete all invalid accounts
"""
import sys
import sqlite3
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.db import DB_PATH
from app.utils.crypto import decrypt_credential


def find_invalid_accounts(account_id=None):
    """Find accounts with corrupt/missing credentials.

    Returns list of tuples: (id, account_name, email_address, is_active, imap_issue, smtp_issue)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if account_id:
        query = "SELECT * FROM email_accounts WHERE id = ?"
        accounts = cursor.execute(query, (account_id,)).fetchall()
    else:
        query = "SELECT * FROM email_accounts ORDER BY id"
        accounts = cursor.execute(query).fetchall()

    invalid = []
    for acc in accounts:
        imap_issue = None
        smtp_issue = None

        # Check IMAP credentials
        if not acc['imap_username']:
            imap_issue = "Missing username"
        elif not acc['imap_password']:
            imap_issue = "Missing encrypted password"
        else:
            imap_pwd = decrypt_credential(acc['imap_password'])
            if not imap_pwd:
                imap_issue = "Corrupt encrypted password (decrypts to None/empty)"

        # Check SMTP credentials
        if not acc['smtp_username']:
            smtp_issue = "Missing username"
        elif not acc['smtp_password']:
            smtp_issue = "Missing encrypted password"
        else:
            smtp_pwd = decrypt_credential(acc['smtp_password'])
            if not smtp_pwd:
                smtp_issue = "Corrupt encrypted password (decrypts to None/empty)"

        # If either IMAP or SMTP has issues, mark as invalid
        if imap_issue or smtp_issue:
            invalid.append({
                'id': acc['id'],
                'account_name': acc['account_name'],
                'email_address': acc['email_address'],
                'is_active': acc['is_active'],
                'imap_issue': imap_issue,
                'smtp_issue': smtp_issue
            })

    conn.close()
    return invalid


def delete_accounts(account_ids):
    """Delete accounts by ID list"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for acc_id in account_ids:
        cursor.execute("DELETE FROM email_accounts WHERE id = ?", (acc_id,))
        print(f"  ✓ Deleted account ID={acc_id}")

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Clean up email accounts with invalid/corrupt credentials",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true', help="Show what would be deleted without deleting")
    parser.add_argument('--id', type=int, help="Only check/delete specific account ID")

    args = parser.parse_args()

    print("=" * 70)
    print("Invalid Account Cleanup Script")
    print("=" * 70)
    print()

    # Find invalid accounts
    if args.id:
        print(f"Checking account ID={args.id}...")
    else:
        print("Scanning all accounts for invalid credentials...")

    invalid = find_invalid_accounts(args.id)

    if not invalid:
        print("✅ No invalid accounts found. All credentials are valid.")
        return 0

    # Display findings
    print(f"\n⚠️  Found {len(invalid)} invalid account(s):\n")
    for acc in invalid:
        print(f"ID: {acc['id']}")
        print(f"  Name: {acc['account_name']}")
        print(f"  Email: {acc['email_address']}")
        print(f"  Active: {'Yes' if acc['is_active'] else 'No'}")
        if acc['imap_issue']:
            print(f"  IMAP Issue: {acc['imap_issue']}")
        if acc['smtp_issue']:
            print(f"  SMTP Issue: {acc['smtp_issue']}")
        print()

    # Dry-run or delete
    if args.dry_run:
        print("🔍 DRY-RUN MODE: No accounts were deleted.")
        print(f"\nTo delete these accounts, run:")
        if args.id:
            print(f"  python scripts/cleanup_invalid_accounts.py --id {args.id}")
        else:
            print(f"  python scripts/cleanup_invalid_accounts.py")
        return 0

    # Confirm deletion
    account_ids = [acc['id'] for acc in invalid]
    if len(account_ids) == 1:
        confirm_msg = f"\n🗑️  Delete account ID={account_ids[0]}? [y/N]: "
    else:
        confirm_msg = f"\n🗑️  Delete {len(account_ids)} accounts? [y/N]: "

    try:
        response = input(confirm_msg).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n\nCancelled by user.")
        return 1

    if response in ('y', 'yes'):
        delete_accounts(account_ids)
        print(f"\n✅ Successfully deleted {len(account_ids)} invalid account(s).")
        return 0
    else:
        print("\nCancelled by user. No accounts were deleted.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
