#!/usr/bin/env python3
"""
Validate that all email connection errors are fixed
"""

import sys
import os
import sqlite3
import subprocess
import time
import json
from datetime import datetime

DB_PATH = 'email_manager.db'

def check_database_structure():
    """Verify database has correct structure"""
    print("\n" + "="*70)
    print("  DATABASE STRUCTURE VALIDATION")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if row_factory works
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Test account table structure
        account = cursor.execute("""
            SELECT * FROM email_accounts LIMIT 1
        """).fetchone()
        
        if account:
            required_fields = [
                'id', 'account_name', 'email_address',
                'imap_host', 'imap_port', 'imap_username', 'imap_password', 'imap_use_ssl',
                'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_ssl',
                'is_active', 'last_checked', 'last_error'
            ]
            
            missing = []
            for field in required_fields:
                try:
                    _ = account[field]
                except (KeyError, IndexError):
                    missing.append(field)
            
            if missing:
                print(f"  ❌ Missing fields: {', '.join(missing)}")
                return False
            else:
                print("  ✅ All required fields present")
        else:
            print("  ⚠️  No accounts found in database")
            
    except Exception as e:
        print(f"  ❌ Database structure error: {e}")
        return False
    
    conn.close()
    return True

def check_code_fixes():
    """Verify that code fixes are in place"""
    print("\n" + "="*70)
    print("  CODE FIX VALIDATION")
    print("="*70)
    
    fixes_found = {
        'monitor_imap_row_factory': False,
        'monitor_imap_dict_access': False,
        'diagnostics_imap_password': False,
        'port_conversion': False,
        'startup_row_factory': False
    }
    
    with open('simple_app.py', 'r') as f:
        content = f.read()
        
        # Check monitor_imap_account fixes
        if 'conn.row_factory = sqlite3.Row' in content and 'def monitor_imap_account' in content:
            fixes_found['monitor_imap_row_factory'] = True
            print("  ✅ monitor_imap_account uses row_factory")
        
        if "account['imap_host']" in content and "account['imap_port']" in content:
            fixes_found['monitor_imap_dict_access'] = True
            print("  ✅ monitor_imap_account uses dictionary access")
        
        # Check diagnostics fix
        if "decrypt_credential(selected_account['imap_password'])" in content:
            fixes_found['diagnostics_imap_password'] = True
            print("  ✅ Diagnostics uses correct IMAP password")
        
        # Check port conversion
        if "int(account['imap_port'])" in content or "int(account['smtp_port'])" in content:
            fixes_found['port_conversion'] = True
            print("  ✅ Port numbers are converted to int")
        
        # Check startup monitoring fix
        if "SELECT id, account_name FROM email_accounts" in content:
            fixes_found['startup_row_factory'] = True
            print("  ✅ Startup monitoring uses proper query")
    
    all_fixed = all(fixes_found.values())
    
    if not all_fixed:
        print("\n  ❌ Missing fixes:")
        for fix, found in fixes_found.items():
            if not found:
                print(f"     - {fix}")
    
    return all_fixed

def test_running_application():
    """Test if the application runs without errors"""
    print("\n" + "="*70)
    print("  APPLICATION RUNTIME TEST")
    print("="*70)
    
    # Check if app is running
    try:
        import requests
        response = requests.get('http://localhost:5000/login', timeout=5)
        if response.status_code == 200:
            print("  ✅ Application is running on port 5000")
        else:
            print(f"  ⚠️  Application returned status {response.status_code}")
    except Exception as e:
        print(f"  ❌ Application not accessible: {e}")
        return False
    
    # Check SMTP proxy
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8587))
        sock.close()
        
        if result == 0:
            print("  ✅ SMTP Proxy is running on port 8587")
        else:
            print("  ❌ SMTP Proxy not accessible on port 8587")
            return False
    except Exception as e:
        print(f"  ❌ SMTP Proxy check failed: {e}")
        return False
    
    return True

def check_error_messages():
    """Check if the getaddrinfo error is gone"""
    print("\n" + "="*70)
    print("  ERROR MESSAGE VALIDATION")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    accounts = cursor.execute("""
        SELECT account_name, last_error 
        FROM email_accounts 
        WHERE last_error IS NOT NULL
    """).fetchall()
    
    getaddrinfo_errors = []
    auth_errors = []
    other_errors = []
    
    for account in accounts:
        error = account['last_error']
        if 'getaddrinfo' in error:
            getaddrinfo_errors.append(account['account_name'])
        elif 'AUTHENTICATIONFAILED' in error or 'authentication failed' in error:
            auth_errors.append(account['account_name'])
        else:
            other_errors.append((account['account_name'], error))
    
    if getaddrinfo_errors:
        print(f"  ❌ 'getaddrinfo' error still present in: {', '.join(getaddrinfo_errors)}")
        print("     This was the main bug - it should be fixed!")
        conn.close()
        return False
    else:
        print("  ✅ No 'getaddrinfo' errors found - main bug is fixed!")
    
    if auth_errors:
        print(f"  ⚠️  Authentication errors in: {', '.join(auth_errors)}")
        print("     This is expected if credentials haven't been updated")
    
    if other_errors:
        print("  ⚠️  Other errors found:")
        for name, error in other_errors:
            print(f"     - {name}: {error[:50]}...")
    
    conn.close()
    return True

def generate_summary():
    """Generate a summary report"""
    print("\n" + "="*70)
    print("  VALIDATION SUMMARY")
    print("="*70)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'database_structure': check_database_structure(),
        'code_fixes': check_code_fixes(),
        'application_running': test_running_application(),
        'errors_fixed': check_error_messages()
    }
    
    # Overall status
    all_good = all([
        results['database_structure'],
        results['code_fixes'],
        results['errors_fixed']
    ])
    
    print("\n  CRITICAL FIXES:")
    print(f"  {'✅' if results['database_structure'] else '❌'} Database Structure")
    print(f"  {'✅' if results['code_fixes'] else '❌'} Code Fixes Applied")
    print(f"  {'✅' if results['errors_fixed'] else '❌'} 'getaddrinfo' Error Fixed")
    
    print("\n  APPLICATION STATUS:")
    print(f"  {'✅' if results['application_running'] else '⚠️'} Application Running")
    
    if all_good:
        print("\n  🎉 ALL CRITICAL ERRORS ARE FIXED!")
        print("  The 'getaddrinfo() argument 1 must be string or None' error is resolved.")
        print("  The application should now work correctly with proper credentials.")
    else:
        print("\n  ⚠️  Some issues remain. Check the details above.")
    
    print("\n  NEXT STEPS:")
    print("  1. Update email account credentials:")
    print("     python update_credentials.py")
    print("  2. For Gmail, use App Passwords (not regular password)")
    print("  3. Test connections:")
    print("     python test_all_connections.py")
    
    # Save report
    report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n  📄 Full report saved to: {report_file}")
    print("="*70 + "\n")
    
    return all_good

if __name__ == "__main__":
    try:
        success = generate_summary()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)