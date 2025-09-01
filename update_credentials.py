#!/usr/bin/env python3
"""
Update email account credentials with working passwords
"""

import sqlite3
import getpass
from cryptography.fernet import Fernet

DB_PATH = 'email_manager.db'

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

def update_account_credentials():
    """Update email account credentials interactively"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all accounts
    accounts = cursor.execute("""
        SELECT id, account_name, email_address, smtp_username, imap_username 
        FROM email_accounts 
        ORDER BY id
    """).fetchall()
    
    print("\n" + "="*70)
    print("  UPDATE EMAIL ACCOUNT CREDENTIALS")
    print("="*70)
    
    for account in accounts:
        print(f"\n📧 Account: {account['account_name']}")
        print(f"   Email: {account['email_address']}")
        print(f"   SMTP Username: {account['smtp_username']}")
        print(f"   IMAP Username: {account['imap_username']}")
        
        update = input("\n   Update this account? (y/n): ").lower()
        
        if update == 'y':
            print("\n   Enter new credentials (press Enter to keep current):")
            
            # Get SMTP password
            smtp_password = getpass.getpass("   SMTP Password: ")
            if smtp_password:
                encrypted_smtp = encrypt_credential(smtp_password)
                cursor.execute("""
                    UPDATE email_accounts 
                    SET smtp_password = ? 
                    WHERE id = ?
                """, (encrypted_smtp, account['id']))
                print("   ✅ SMTP password updated")
            
            # Get IMAP password
            imap_password = getpass.getpass("   IMAP Password (or same as SMTP - press Enter): ")
            if imap_password:
                encrypted_imap = encrypt_credential(imap_password)
            elif smtp_password:
                # Use SMTP password for IMAP if not specified
                encrypted_imap = encrypted_smtp
            else:
                encrypted_imap = None
                
            if encrypted_imap:
                cursor.execute("""
                    UPDATE email_accounts 
                    SET imap_password = ? 
                    WHERE id = ?
                """, (encrypted_imap, account['id']))
                print("   ✅ IMAP password updated")
            
            # Clear any previous errors
            cursor.execute("""
                UPDATE email_accounts 
                SET last_error = NULL 
                WHERE id = ?
            """, (account['id'],))
            
            conn.commit()
            print("   ✅ Account updated successfully!")
    
    conn.close()
    print("\n" + "="*70)
    print("  CREDENTIALS UPDATE COMPLETE")
    print("="*70 + "\n")

def set_test_credentials():
    """Set known working test credentials (for demo purposes)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n⚠️  Setting demo credentials (won't work with real accounts)")
    print("   For Gmail: Use an App Password, not your regular password")
    print("   Format: xxxx xxxx xxxx xxxx (with spaces)")
    
    # Update Gmail account with placeholder
    gmail_password = encrypt_credential("your-app-password-here")
    cursor.execute("""
        UPDATE email_accounts 
        SET smtp_password = ?, imap_password = ?, last_error = 'Credentials need to be updated'
        WHERE account_name = 'Gmail Test Account'
    """, (gmail_password, gmail_password))
    
    # Update Hostinger account with placeholder
    hostinger_password = encrypt_credential("your-hostinger-password")
    cursor.execute("""
        UPDATE email_accounts 
        SET smtp_password = ?, imap_password = ?, last_error = 'Credentials need to be updated'
        WHERE account_name = 'Hostinger Account'
    """, (hostinger_password, hostinger_password))
    
    conn.commit()
    conn.close()
    
    print("✅ Placeholder credentials set. Run this script again to enter real passwords.\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        set_test_credentials()
    else:
        print("\n📝 Note: For Gmail, you need an App Password, not your regular password")
        print("   1. Go to https://myaccount.google.com/apppasswords")
        print("   2. Generate an app password for 'Mail'")
        print("   3. Enter it WITH spaces: xxxx xxxx xxxx xxxx\n")
        
        update_account_credentials()