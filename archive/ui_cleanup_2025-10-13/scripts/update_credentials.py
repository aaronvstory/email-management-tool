#!/usr/bin/env python3
"""
Update email account credentials with proper encryption and SMTP/IMAP settings.
Uses confirmed working credentials from CLAUDE.md.
"""

import sqlite3
import sys
import os

# Add parent directory to path to import crypto module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.crypto import encrypt_password

DB_PATH = 'email_manager.db'

def update_account_credentials():
    """Update both Gmail and Hostinger accounts with confirmed working credentials"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 70)
    print("UPDATING EMAIL ACCOUNT CREDENTIALS")
    print("=" * 70)

    # Account 1: Gmail - NDayijecika
    print("\n[1/3] Updating Gmail - NDayijecika account...")
    gmail_password = "bjormgplhgwkgpad"  # Confirmed working App Password
    gmail_encrypted = encrypt_password(gmail_password)

    cursor.execute("""
        UPDATE email_accounts
        SET smtp_username = ?,
            smtp_password = ?,
            smtp_host = ?,
            smtp_port = ?,
            smtp_use_ssl = ?,
            imap_host = ?,
            imap_port = ?,
            imap_use_ssl = ?
        WHERE id = 3
    """, (
        'ndayijecika@gmail.com',
        gmail_encrypted,
        'smtp.gmail.com',
        587,
        0,  # STARTTLS for port 587
        'imap.gmail.com',
        993,
        1   # SSL for IMAP
    ))
    print("   ✅ Gmail credentials updated (SMTP: 587/STARTTLS, IMAP: 993/SSL)")

    # Account 2: Hostinger - Corrinbox
    print("\n[2/3] Updating Hostinger - Corrinbox account...")
    hostinger_password = "25Horses807$"  # Confirmed working password
    hostinger_encrypted = encrypt_password(hostinger_password)

    cursor.execute("""
        UPDATE email_accounts
        SET smtp_username = ?,
            smtp_password = ?,
            smtp_host = ?,
            smtp_port = ?,
            smtp_use_ssl = ?,
            imap_host = ?,
            imap_port = ?,
            imap_use_ssl = ?
        WHERE id = 2
    """, (
        'mcintyre@corrinbox.com',
        hostinger_encrypted,
        'smtp.hostinger.com',
        465,
        1,  # Direct SSL for port 465
        'imap.hostinger.com',
        993,
        1   # SSL for IMAP
    ))
    print("   ✅ Hostinger credentials updated (SMTP: 465/SSL, IMAP: 993/SSL)")

    # Delete placeholder emails
    print("\n[3/3] Deleting placeholder test emails...")
    cursor.execute("""
        DELETE FROM email_messages
        WHERE sender LIKE '%test%'
           OR sender LIKE '%example%'
           OR recipients LIKE '%example%'
    """)
    deleted_count = cursor.rowcount
    print(f"   ✅ Deleted {deleted_count} placeholder emails")

    conn.commit()
    conn.close()

    print("\n" + "=" * 70)
    print("CREDENTIAL UPDATE COMPLETE")
    print("=" * 70)
    print("\n✅ Both accounts ready for testing")
    print("✅ Database cleaned of placeholder data")
    print("✅ SMTP/IMAP ports configured correctly")
    print("\nNext steps:")
    print("1. Restart application: python simple_app.py")
    print("2. Test Gmail account: ndayijecika@gmail.com")
    print("3. Test Hostinger account: mcintyre@corrinbox.com")
    print()

if __name__ == '__main__':
    try:
        update_account_credentials()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
