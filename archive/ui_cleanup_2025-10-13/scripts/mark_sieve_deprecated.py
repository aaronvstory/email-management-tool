"""
Mark Sieve Status as Deprecated in Database

This script updates all email accounts to mark their sieve_status as 'deprecated'
and clears sieve_endpoint values. This is part of the v2.0 migration to IMAP-only
interception.

Safe to run multiple times (idempotent).
"""
import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = "email_manager.db"


def mark_deprecated():
    """Mark all Sieve statuses as deprecated"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        print("   Run this script from the project root directory.")
        return False

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Check if sieve_status column exists
        cur.execute("PRAGMA table_info(email_accounts)")
        columns = [row[1] for row in cur.fetchall()]

        if 'sieve_status' not in columns:
            print("✓ sieve_status column does not exist (already removed or never added)")
            conn.close()
            return True

        # Count accounts with non-deprecated Sieve status
        cur.execute("""
            SELECT COUNT(*) FROM email_accounts
            WHERE sieve_status IS NOT NULL AND sieve_status != 'deprecated'
        """)
        affected_count = cur.fetchone()[0]

        if affected_count == 0:
            print("✓ All accounts already have sieve_status='deprecated' or NULL")
            conn.close()
            return True

        # Update sieve_status to 'deprecated'
        cur.execute("""
            UPDATE email_accounts
            SET sieve_status = 'deprecated',
                sieve_endpoint = NULL
            WHERE sieve_status IS NOT NULL AND sieve_status != 'deprecated'
        """)

        # Also ensure interception_mode is set to 'imap' if present
        if 'interception_mode' in columns:
            cur.execute("""
                UPDATE email_accounts
                SET interception_mode = 'imap'
                WHERE interception_mode IS NULL OR interception_mode != 'imap'
            """)

        conn.commit()

        print(f"✅ Successfully updated {affected_count} account(s)")
        print("   - sieve_status set to 'deprecated'")
        print("   - sieve_endpoint set to NULL")
        if 'interception_mode' in columns:
            print("   - interception_mode set to 'imap'")

        # Show updated accounts
        cur.execute("""
            SELECT id, account_name, email_address, sieve_status
            FROM email_accounts
            ORDER BY id
        """)
        accounts = cur.fetchall()

        if accounts:
            print("\nUpdated accounts:")
            for row in accounts:
                print(f"  [{row[0]}] {row[1]} ({row[2]}) - sieve_status: {row[3]}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("  MARK SIEVE DEPRECATED SCRIPT (v2.0)")
    print("=" * 70)
    print()

    success = mark_deprecated()

    print()
    print("=" * 70)
    if success:
        print("  ✅ MIGRATION COMPLETE")
    else:
        print("  ❌ MIGRATION FAILED")
    print("=" * 70)

    sys.exit(0 if success else 1)