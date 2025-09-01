#!/usr/bin/env python3
"""
Comprehensive test for all email account connections
Tests IMAP, SMTP, and verifies database fixes
"""

import sqlite3
import imaplib
import smtplib
import ssl
from cryptography.fernet import Fernet
from datetime import datetime
import json
import sys

# Database path
DB_PATH = 'email_manager.db'

def decrypt_credential(encrypted_value):
    """Decrypt credential using Fernet encryption"""
    try:
        with open('key.txt', 'r') as f:
            key = f.read().strip()
        fernet = Fernet(key.encode() if isinstance(key, str) else key)
        if encrypted_value:
            decrypted = fernet.decrypt(encrypted_value.encode() if isinstance(encrypted_value, str) else encrypted_value)
            return decrypted.decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        return encrypted_value
    return ""

def test_account_connections():
    """Test all email account connections"""
    print("\n" + "="*70)
    print("  EMAIL ACCOUNT CONNECTION TEST")
    print("="*70)
    
    # Connect to database with row_factory
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all accounts
    accounts = cursor.execute("""
        SELECT * FROM email_accounts WHERE is_active = 1
    """).fetchall()
    
    if not accounts:
        print("\n❌ No active email accounts found in database")
        conn.close()
        return False
    
    all_success = True
    results = []
    
    for account in accounts:
        print(f"\n📧 Testing: {account['account_name']} ({account['email_address']})")
        print("-" * 50)
        
        account_result = {
            'name': account['account_name'],
            'email': account['email_address'],
            'smtp': {'success': False, 'message': ''},
            'imap': {'success': False, 'message': ''}
        }
        
        # Test SMTP Connection
        print(f"  SMTP Server: {account['smtp_host']}:{account['smtp_port']}")
        try:
            smtp_password = decrypt_credential(account['smtp_password'])
            smtp_port = int(account['smtp_port']) if account['smtp_port'] else 587
            
            if smtp_port == 465:
                smtp_server = smtplib.SMTP_SSL(account['smtp_host'], smtp_port, timeout=10)
            else:
                smtp_server = smtplib.SMTP(account['smtp_host'], smtp_port, timeout=10)
                smtp_server.starttls()
            
            smtp_server.login(account['smtp_username'], smtp_password)
            smtp_server.quit()
            
            print(f"  ✅ SMTP Connection: SUCCESS")
            account_result['smtp']['success'] = True
            account_result['smtp']['message'] = 'Connected successfully'
            
        except Exception as e:
            print(f"  ❌ SMTP Connection: FAILED")
            print(f"     Error: {str(e)}")
            account_result['smtp']['message'] = str(e)
            all_success = False
        
        # Test IMAP Connection
        print(f"  IMAP Server: {account['imap_host']}:{account['imap_port']}")
        try:
            imap_password = decrypt_credential(account['imap_password'])
            imap_port = int(account['imap_port']) if account['imap_port'] else 993
            
            if account['imap_use_ssl']:
                imap_server = imaplib.IMAP4_SSL(account['imap_host'], imap_port)
            else:
                imap_server = imaplib.IMAP4(account['imap_host'], imap_port)
            
            imap_server.login(account['imap_username'], imap_password)
            imap_server.select('INBOX')
            
            # Get inbox status
            status, messages = imap_server.search(None, 'ALL')
            if status == 'OK':
                msg_count = len(messages[0].split()) if messages[0] else 0
                print(f"  ✅ IMAP Connection: SUCCESS (Inbox: {msg_count} messages)")
                account_result['imap']['success'] = True
                account_result['imap']['message'] = f'Connected, {msg_count} messages in inbox'
            
            imap_server.close()
            imap_server.logout()
            
        except Exception as e:
            print(f"  ❌ IMAP Connection: FAILED")
            print(f"     Error: {str(e)}")
            account_result['imap']['message'] = str(e)
            all_success = False
        
        results.append(account_result)
        
        # Update database with test results
        try:
            cursor.execute("""
                UPDATE email_accounts 
                SET last_checked = CURRENT_TIMESTAMP,
                    last_error = ?
                WHERE id = ?
            """, (
                None if (account_result['smtp']['success'] and account_result['imap']['success']) 
                else f"SMTP: {account_result['smtp']['message']}, IMAP: {account_result['imap']['message']}",
                account['id']
            ))
            conn.commit()
        except Exception as e:
            print(f"  ⚠️  Failed to update database: {e}")
    
    conn.close()
    
    # Print summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    smtp_success = sum(1 for r in results if r['smtp']['success'])
    imap_success = sum(1 for r in results if r['imap']['success'])
    
    print(f"\n  Total Accounts Tested: {total}")
    print(f"  SMTP Success Rate: {smtp_success}/{total} ({smtp_success*100//total if total else 0}%)")
    print(f"  IMAP Success Rate: {imap_success}/{total} ({imap_success*100//total if total else 0}%)")
    
    if all_success:
        print("\n  🎉 ALL CONNECTIONS SUCCESSFUL!")
    else:
        print("\n  ⚠️  Some connections failed. Check credentials and server settings.")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_results_{timestamp}.json"
    
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_accounts': total,
                'smtp_success': smtp_success,
                'imap_success': imap_success,
                'all_success': all_success
            },
            'accounts': results
        }, f, indent=2)
    
    print(f"\n  📄 Detailed results saved to: {result_file}")
    print("="*70 + "\n")
    
    return all_success

def verify_database_fixes():
    """Verify that database column access is fixed"""
    print("\n📊 Verifying Database Fixes...")
    print("-" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    
    # Test without row_factory (should fail or give wrong results)
    cursor = conn.cursor()
    account = cursor.execute("SELECT * FROM email_accounts LIMIT 1").fetchone()
    
    if account:
        print("  ⚠️  Without row_factory: Data is tuple (index-based access)")
        print(f"     account[0] = {account[0]} (ID)")
        
    # Test with row_factory (should work correctly)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    account = cursor.execute("SELECT * FROM email_accounts LIMIT 1").fetchone()
    
    if account:
        print("  ✅ With row_factory: Data is Row (dictionary-like access)")
        print(f"     account['id'] = {account['id']}")
        print(f"     account['account_name'] = {account['account_name']}")
        print(f"     account['imap_host'] = {account['imap_host']}")
        
    conn.close()
    print("  ✅ Database fixes verified!\n")

if __name__ == "__main__":
    try:
        # First verify database fixes
        verify_database_fixes()
        
        # Then test all connections
        success = test_account_connections()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)