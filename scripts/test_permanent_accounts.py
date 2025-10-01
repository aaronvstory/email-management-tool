#!/usr/bin/env python3
"""
Test Permanent Account Connections
Tests both Gmail and Hostinger accounts with smart-detected settings
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import imaplib
import smtplib
from datetime import datetime

# Test account credentials (from CLAUDE.md)
ACCOUNTS = [
    {
        'name': 'Gmail - NDayijecika',
        'email': 'ndayijecika@gmail.com',
        'password': 'bjormgplhgwkgpad',
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_ssl': False,  # STARTTLS
        'imap_host': 'imap.gmail.com',
        'imap_port': 993
    },
    {
        'name': 'Hostinger - Corrinbox',
        'email': 'mcintyre@corrinbox.com',
        'password': '25Horses807$',
        'smtp_host': 'smtp.hostinger.com',
        'smtp_port': 465,
        'smtp_ssl': True,  # Direct SSL
        'imap_host': 'imap.hostinger.com',
        'imap_port': 993
    }
]

def test_imap(host, port, username, password):
    """Test IMAP connection"""
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(username, password)
        status, folders = mail.list()
        mail.logout()
        return True, f"Connected, found {len(folders)} folders"
    except Exception as e:
        return False, str(e)

def test_smtp(host, port, username, password, use_ssl):
    """Test SMTP connection"""
    try:
        if use_ssl:
            # Direct SSL (port 465)
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            # STARTTLS (port 587)
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()

        server.login(username, password)
        server.quit()
        return True, "Connected and authenticated"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 80)
    print("PERMANENT TEST ACCOUNTS - CONNECTION TEST")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    for acc in ACCOUNTS:
        print(f"\n{'─' * 80}")
        print(f"Testing: {acc['name']}")
        print(f"Email: {acc['email']}")
        print(f"{'─' * 80}")

        # Test IMAP
        print(f"\n📬 Testing IMAP ({acc['imap_host']}:{acc['imap_port']})...")
        imap_ok, imap_msg = test_imap(
            acc['imap_host'],
            acc['imap_port'],
            acc['email'],
            acc['password']
        )

        if imap_ok:
            print(f"   ✅ IMAP SUCCESS: {imap_msg}")
        else:
            print(f"   ❌ IMAP FAILED: {imap_msg}")

        # Test SMTP
        ssl_type = "SSL" if acc['smtp_ssl'] else "STARTTLS"
        print(f"\n📤 Testing SMTP ({acc['smtp_host']}:{acc['smtp_port']} {ssl_type})...")
        smtp_ok, smtp_msg = test_smtp(
            acc['smtp_host'],
            acc['smtp_port'],
            acc['email'],
            acc['password'],
            acc['smtp_ssl']
        )

        if smtp_ok:
            print(f"   ✅ SMTP SUCCESS: {smtp_msg}")
        else:
            print(f"   ❌ SMTP FAILED: {smtp_msg}")

        # Overall status
        print(f"\n{'─' * 80}")
        if imap_ok and smtp_ok:
            print("✅ ACCOUNT FULLY OPERATIONAL")
        else:
            print("⚠️  ACCOUNT HAS ISSUES - Check errors above")

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nIf all tests passed, these accounts are ready for use in the Email Manager.")
    print("Run 'python scripts/setup_test_accounts.py' to add them to the database.")

if __name__ == '__main__':
    main()
