#!/usr/bin/env python3
"""
Comprehensive System Testing Script
Tests authentication, IMAP connections, database operations, and system health
"""

import sqlite3
import imaplib
import smtplib
import time
import json
import sys
from datetime import datetime
from app.utils.crypto import decrypt_credential

DB_PATH = "email_manager.db"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_database_connectivity():
    """Test database connectivity and schema"""
    print_section("1. DATABASE CONNECTIVITY TEST")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Test tables exist
        tables = ['users', 'email_accounts', 'email_messages', 'moderation_rules', 'audit_log']
        results = {}
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            results[table] = count
            print(f"✓ Table '{table}': {count} rows")
        
        conn.close()
        return True, results
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False, str(e)

def test_credential_encryption():
    """Test credential encryption/decryption"""
    print_section("2. CREDENTIAL ENCRYPTION TEST")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, account_name, email_address, imap_password FROM email_accounts WHERE is_active=1")
        accounts = cursor.fetchall()
        
        results = []
        for account in accounts:
            encrypted_pwd = account['imap_password']
            decrypted_pwd = decrypt_credential(encrypted_pwd)
            
            result = {
                'id': account['id'],
                'name': account['account_name'],
                'email': account['email_address'],
                'encrypted_length': len(encrypted_pwd) if encrypted_pwd else 0,
                'decrypted': bool(decrypted_pwd),
                'decrypted_length': len(decrypted_pwd) if decrypted_pwd else 0
            }
            results.append(result)
            
            status = "✓" if decrypted_pwd else "✗"
            print(f"{status} Account {account['id']} ({account['email_address']})")
            print(f"   Encrypted length: {result['encrypted_length']} bytes")
            print(f"   Decryption: {'SUCCESS' if decrypted_pwd else 'FAILED'}")
            if decrypted_pwd:
                print(f"   Decrypted length: {result['decrypted_length']} chars")
        
        conn.close()
        return True, results
    except Exception as e:
        print(f"✗ Encryption test error: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def test_imap_connections():
    """Test IMAP connections for all active accounts"""
    print_section("3. IMAP CONNECTION TEST")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, account_name, email_address, imap_host, imap_port, 
                   imap_username, imap_password, imap_use_ssl 
            FROM email_accounts WHERE is_active=1
        """)
        accounts = cursor.fetchall()
        conn.close()
        
        results = []
        for account in accounts:
            account_id = account['id']
            email = account['email_address']
            
            print(f"\nTesting Account {account_id}: {email}")
            print(f"  Host: {account['imap_host']}:{account['imap_port']}")
            print(f"  Username: {account['imap_username']}")
            print(f"  SSL: {bool(account['imap_use_ssl'])}")
            
            try:
                # Decrypt password
                encrypted_pwd = account['imap_password']
                password = decrypt_credential(encrypted_pwd)
                
                if not password:
                    print(f"  ✗ Password decryption failed")
                    results.append({
                        'id': account_id,
                        'email': email,
                        'success': False,
                        'error': 'Password decryption failed'
                    })
                    continue
                
                # Try IMAP connection
                start_time = time.time()
                
                if account['imap_use_ssl']:
                    imap = imaplib.IMAP4_SSL(account['imap_host'], account['imap_port'])
                else:
                    imap = imaplib.IMAP4(account['imap_host'], account['imap_port'])
                
                # Attempt login
                imap.login(account['imap_username'], password)
                
                # List folders
                status, folders = imap.list()
                folder_count = len(folders) if folders else 0
                
                # Select INBOX
                status, messages = imap.select('INBOX')
                message_count = int(messages[0]) if messages else 0
                
                imap.logout()
                
                elapsed = time.time() - start_time
                
                print(f"  ✓ Connection SUCCESS ({elapsed:.2f}s)")
                print(f"  ✓ Folders: {folder_count}")
                print(f"  ✓ INBOX messages: {message_count}")
                
                results.append({
                    'id': account_id,
                    'email': email,
                    'success': True,
                    'folders': folder_count,
                    'messages': message_count,
                    'latency_ms': int(elapsed * 1000)
                })
                
            except Exception as e:
                error_msg = str(e)
                print(f"  ✗ Connection FAILED: {error_msg}")
                results.append({
                    'id': account_id,
                    'email': email,
                    'success': False,
                    'error': error_msg
                })
        
        return True, results
    except Exception as e:
        print(f"✗ IMAP test error: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def test_smtp_proxy():
    """Test SMTP proxy availability"""
    print_section("4. SMTP PROXY TEST")
    
    try:
        smtp = smtplib.SMTP('localhost', 8587, timeout=5)
        smtp.quit()
        print("✓ SMTP proxy is running on port 8587")
        return True, "SMTP proxy available"
    except Exception as e:
        print(f"✗ SMTP proxy connection failed: {e}")
        return False, str(e)

def test_database_operations():
    """Test database read/write operations"""
    print_section("5. DATABASE OPERATIONS TEST")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Test write operation
        test_data = f"test_{int(time.time())}"
        cursor.execute("""
            INSERT INTO audit_log (action, user_id, target_id, details, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, ('SYSTEM_TEST', 1, 0, test_data))
        conn.commit()
        
        # Test read operation
        cursor.execute("SELECT details FROM audit_log WHERE details=?", (test_data,))
        result = cursor.fetchone()
        
        # Cleanup
        cursor.execute("DELETE FROM audit_log WHERE details=?", (test_data,))
        conn.commit()
        conn.close()
        
        if result and result[0] == test_data:
            print("✓ Write operation: SUCCESS")
            print("✓ Read operation: SUCCESS")
            print("✓ Delete operation: SUCCESS")
            return True, "All database operations working"
        else:
            print("✗ Database operations failed")
            return False, "Data verification failed"
            
    except Exception as e:
        print(f"✗ Database operations error: {e}")
        return False, str(e)

def test_email_messages():
    """Test email message storage"""
    print_section("6. EMAIL MESSAGES TEST")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Count messages by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM email_messages 
            GROUP BY status
        """)
        status_counts = cursor.fetchall()
        
        # Count by interception status
        cursor.execute("""
            SELECT interception_status, COUNT(*) as count 
            FROM email_messages 
            WHERE interception_status IS NOT NULL
            GROUP BY interception_status
        """)
        interception_counts = cursor.fetchall()
        
        # Get recent messages
        cursor.execute("""
            SELECT id, subject, sender, status, interception_status, created_at
            FROM email_messages
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent = cursor.fetchall()
        
        conn.close()
        
        print("Message counts by status:")
        for row in status_counts:
            print(f"  {row['status']}: {row['count']}")
        
        if interception_counts:
            print("\nInterception status counts:")
            for row in interception_counts:
                print(f"  {row['interception_status']}: {row['count']}")
        
        if recent:
            print("\nMost recent messages:")
            for msg in recent:
                print(f"  ID {msg['id']}: {msg['subject'][:50]} ({msg['status']}/{msg['interception_status'] or 'N/A'})")
        
        return True, {
            'status_counts': [dict(row) for row in status_counts],
            'interception_counts': [dict(row) for row in interception_counts],
            'recent_count': len(recent)
        }
    except Exception as e:
        print(f"✗ Email messages test error: {e}")
        return False, str(e)

def main():
    """Run all tests and generate report"""
    print("\n" + "="*80)
    print("  COMPREHENSIVE SYSTEM TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)
    
    results = {}
    
    # Run all tests
    results['database_connectivity'] = test_database_connectivity()
    results['credential_encryption'] = test_credential_encryption()
    results['imap_connections'] = test_imap_connections()
    results['smtp_proxy'] = test_smtp_proxy()
    results['database_operations'] = test_database_operations()
    results['email_messages'] = test_email_messages()
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for success, _ in results.values() if success)
    total = len(results)
    
    for test_name, (success, data) in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    # Save detailed results
    output_file = f"test_results_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {'passed': passed, 'total': total, 'percentage': passed/total*100},
            'results': {k: {'success': v[0], 'data': v[1]} for k, v in results.items()}
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())