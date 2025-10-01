#!/usr/bin/env python3
"""
Setup Permanent Test Accounts
Automatically configures the two permanent test accounts with smart detection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from app.utils.crypto import encrypt_credential
from app.utils.db import DB_PATH

# Permanent test account credentials (from CLAUDE.md)
PERMANENT_ACCOUNTS = [
    {
        'account_name': 'Gmail - NDayijecika (Primary Test)',
        'email_address': 'ndayijecika@gmail.com',
        'password': 'bjormgplhgwkgpad',
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_use_ssl': 0,  # STARTTLS
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'imap_use_ssl': 1
    },
    {
        'account_name': 'Hostinger - Corrinbox (Secondary Test)',
        'email_address': 'mcintyre@corrinbox.com',
        'password': '25Horses807$',
        'smtp_host': 'smtp.hostinger.com',
        'smtp_port': 465,
        'smtp_use_ssl': 1,  # Direct SSL
        'imap_host': 'imap.hostinger.com',
        'imap_port': 993,
        'imap_use_ssl': 1
    }
]

def setup_accounts():
    """Setup the permanent test accounts"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("PERMANENT TEST ACCOUNT SETUP")
    print("=" * 80)

    for acc in PERMANENT_ACCOUNTS:
        email = acc['email_address']

        # Check if account already exists
        existing = cursor.execute(
            "SELECT id, account_name FROM email_accounts WHERE email_address=?",
            (email,)
        ).fetchone()

        if existing:
            print(f"\n✓ Account already exists: {email}")
            print(f"  ID: {existing[0]}, Name: {existing[1]}")

            # Update existing account with correct settings
            encrypted_pwd = encrypt_credential(acc['password'])
            cursor.execute("""
                UPDATE email_accounts SET
                    account_name=?,
                    imap_host=?, imap_port=?, imap_username=?, imap_password=?, imap_use_ssl=?,
                    smtp_host=?, smtp_port=?, smtp_username=?, smtp_password=?, smtp_use_ssl=?,
                    is_active=1
                WHERE email_address=?
            """, (
                acc['account_name'],
                acc['imap_host'], acc['imap_port'], email, encrypted_pwd, acc['imap_use_ssl'],
                acc['smtp_host'], acc['smtp_port'], email, encrypted_pwd, acc['smtp_use_ssl'],
                email
            ))
            print(f"  ✓ Updated with correct smart-detected settings")
        else:
            # Insert new account
            encrypted_pwd = encrypt_credential(acc['password'])
            cursor.execute("""
                INSERT INTO email_accounts (
                    account_name, email_address,
                    imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
                    smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl,
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                acc['account_name'], email,
                acc['imap_host'], acc['imap_port'], email, encrypted_pwd, acc['imap_use_ssl'],
                acc['smtp_host'], acc['smtp_port'], email, encrypted_pwd, acc['smtp_use_ssl']
            ))
            print(f"\n✓ Created new account: {email}")
            print(f"  Name: {acc['account_name']}")

        # Display configuration
        print(f"\n  Configuration:")
        print(f"    SMTP: {acc['smtp_host']}:{acc['smtp_port']} {'(SSL)' if acc['smtp_use_ssl'] else '(STARTTLS)'}")
        print(f"    IMAP: {acc['imap_host']}:{acc['imap_port']} (SSL)")
        print(f"    Username: {email}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("✓ SETUP COMPLETE")
    print("=" * 80)
    print("\nThese accounts are now configured and ready for testing.")
    print("Both accounts use their email address as username.")
    print("\nAccess the web interface at: http://localhost:5000")
    print("Login: admin / admin123")

if __name__ == '__main__':
    setup_accounts()
