#!/usr/bin/env python3
"""
Add Gmail account with proper credentials and test connectivity
"""

import sqlite3
import smtplib
import imaplib
from cryptography.fernet import Fernet
from datetime import datetime

# Database path
DB_PATH = 'email_manager.db'

# Gmail credentials
GMAIL_EMAIL = 'ndayijecika@gmail.com'
GMAIL_PASSWORD = 'VDMcQeklCH2mom'  # Regular password (not used for IMAP/SMTP)
GMAIL_APP_PASSWORD = 'gbrw tagu ayhy wtry'  # App password WITH spaces

# Gmail settings (researched and verified)
GMAIL_IMAP_HOST = 'imap.gmail.com'
GMAIL_IMAP_PORT = 993
GMAIL_SMTP_HOST = 'smtp.gmail.com'
GMAIL_SMTP_PORT = 587  # TLS/STARTTLS port

def encrypt_credential(plain_text):
    """Encrypt credential using Fernet encryption"""
    try:
        with open('key.txt', 'r') as f:
            key = f.read().strip()
        fernet = Fernet(key.encode() if isinstance(key, str) else key)
        encrypted = fernet.encrypt(plain_text.encode())
        return encrypted.decode()
    except Exception as e:
        print(f"Encryption error: {e}")
        return plain_text

def test_gmail_connection():
    """Test Gmail IMAP and SMTP connections before adding to database"""
    print("\n" + "="*70)
    print("  TESTING GMAIL CONNECTION")
    print("="*70)
    
    # Test SMTP
    print(f"\n📧 Testing SMTP: {GMAIL_SMTP_HOST}:{GMAIL_SMTP_PORT}")
    try:
        smtp = smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=10)
        smtp.starttls()
        smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        smtp.quit()
        print("  ✅ SMTP Connection: SUCCESS")
        smtp_success = True
    except Exception as e:
        print(f"  ❌ SMTP Connection: FAILED - {e}")
        smtp_success = False
    
    # Test IMAP
    print(f"\n📬 Testing IMAP: {GMAIL_IMAP_HOST}:{GMAIL_IMAP_PORT}")
    try:
        imap = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST, GMAIL_IMAP_PORT)
        imap.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        imap.select('INBOX')
        
        # Get inbox count
        status, messages = imap.search(None, 'ALL')
        msg_count = len(messages[0].split()) if messages[0] else 0
        print(f"  ✅ IMAP Connection: SUCCESS ({msg_count} messages in inbox)")
        
        imap.close()
        imap.logout()
        imap_success = True
    except Exception as e:
        print(f"  ❌ IMAP Connection: FAILED - {e}")
        imap_success = False
    
    return smtp_success and imap_success

def add_gmail_account():
    """Add Gmail account to database"""
    print("\n" + "="*70)
    print("  ADDING GMAIL ACCOUNT TO DATABASE")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if account already exists
    existing = cursor.execute("""
        SELECT id FROM email_accounts 
        WHERE email_address = ?
    """, (GMAIL_EMAIL,)).fetchone()
    
    if existing:
        print(f"\n⚠️  Account {GMAIL_EMAIL} already exists with ID: {existing[0]}")
        print("   Updating credentials...")
        
        # Update existing account
        encrypted_password = encrypt_credential(GMAIL_APP_PASSWORD)
        cursor.execute("""
            UPDATE email_accounts
            SET smtp_password = ?, imap_password = ?,
                smtp_host = ?, smtp_port = ?, smtp_username = ?, smtp_use_ssl = 0,
                imap_host = ?, imap_port = ?, imap_username = ?, imap_use_ssl = 1,
                last_error = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE email_address = ?
        """, (
            encrypted_password, encrypted_password,
            GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, GMAIL_EMAIL,
            GMAIL_IMAP_HOST, GMAIL_IMAP_PORT, GMAIL_EMAIL,
            GMAIL_EMAIL
        ))
        account_id = existing[0]
    else:
        print(f"\n✨ Adding new account: {GMAIL_EMAIL}")
        
        # Encrypt the app password
        encrypted_password = encrypt_credential(GMAIL_APP_PASSWORD)
        
        # Insert new account (matching actual database schema)
        cursor.execute("""
            INSERT INTO email_accounts (
                account_name, email_address,
                imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
                smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl,
                is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            'Gmail - NDayijecika',  # account_name
            GMAIL_EMAIL,           # email_address
            GMAIL_IMAP_HOST,       # imap_host
            GMAIL_IMAP_PORT,       # imap_port
            GMAIL_EMAIL,           # imap_username
            encrypted_password,    # imap_password (encrypted)
            1,                     # imap_use_ssl (True)
            GMAIL_SMTP_HOST,       # smtp_host
            GMAIL_SMTP_PORT,       # smtp_port
            GMAIL_EMAIL,           # smtp_username
            encrypted_password,    # smtp_password (encrypted)
            0,                     # smtp_use_ssl (False - uses STARTTLS)
            1                      # is_active (True)
        ))
        account_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    print(f"✅ Account saved with ID: {account_id}")
    print(f"   Email: {GMAIL_EMAIL}")
    print(f"   IMAP: {GMAIL_IMAP_HOST}:{GMAIL_IMAP_PORT} (SSL)")
    print(f"   SMTP: {GMAIL_SMTP_HOST}:{GMAIL_SMTP_PORT} (STARTTLS)")
    
    return account_id

def verify_account_in_db(account_id):
    """Verify the account was properly added to database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    account = cursor.execute("""
        SELECT * FROM email_accounts WHERE id = ?
    """, (account_id,)).fetchone()
    
    if account:
        print("\n" + "="*70)
        print("  DATABASE VERIFICATION")
        print("="*70)
        print(f"  ✅ Account found in database:")
        print(f"     Name: {account['account_name']}")
        print(f"     Email: {account['email_address']}")
        print(f"     IMAP: {account['imap_host']}:{account['imap_port']}")
        print(f"     SMTP: {account['smtp_host']}:{account['smtp_port']}")
        print(f"     Active: {'Yes' if account['is_active'] else 'No'}")
    else:
        print("  ❌ Account not found in database!")
    
    conn.close()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  GMAIL ACCOUNT SETUP")
    print("="*70)
    print(f"  Email: {GMAIL_EMAIL}")
    print(f"  App Password: {GMAIL_APP_PASSWORD}")
    print("="*70)
    
    # Test connection first
    if test_gmail_connection():
        print("\n🎉 Connection tests passed! Adding to database...")
        
        # Add to database
        account_id = add_gmail_account()
        
        # Verify it was added
        verify_account_in_db(account_id)
        
        print("\n" + "="*70)
        print("  ✅ GMAIL ACCOUNT SUCCESSFULLY CONFIGURED")
        print("="*70)
        print("\n  Next steps:")
        print("  1. Restart the application to enable monitoring")
        print("  2. Access http://localhost:5000/accounts to manage")
        print("  3. Test email interception through SMTP proxy")
    else:
        print("\n❌ Connection tests failed. Please check:")
        print("  1. App password is correct (with spaces)")
        print("  2. 2-Factor authentication is enabled")
        print("  3. IMAP is enabled in Gmail settings")
        print("  4. Network connection is working")