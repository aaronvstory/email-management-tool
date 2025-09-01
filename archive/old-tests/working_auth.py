#!/usr/bin/env python3
"""
Hostinger Authentication - Working Solution
Using the exact credentials that work in email client
"""

import imaplib
import smtplib
import ssl
import socket

# EXACT WORKING CREDENTIALS
USERNAME = "mcintyre@corrinbox.com"
PASSWORD = "Slaypap3!!"

print("=" * 60)
print("HOSTINGER EMAIL - WORKING AUTHENTICATION")
print("=" * 60)

def test_imap_simple():
    """Simplest possible IMAP test"""
    print("\nTesting IMAP (simplest method)...")
    
    try:
        # Connect without any special SSL settings first
        print(f"  Connecting to imap.hostinger.com:993...")
        M = imaplib.IMAP4_SSL('imap.hostinger.com', 993)
        
        print(f"  Logging in as {USERNAME}...")
        # Use the exact credentials
        typ, data = M.login(USERNAME, PASSWORD)
        
        if typ == 'OK':
            print("  ✅ IMAP LOGIN SUCCESSFUL!")
            
            # List folders
            typ, data = M.list()
            if typ == 'OK':
                print(f"  ✅ Found {len(data)} folders")
            
            # Select INBOX
            typ, data = M.select('INBOX')
            if typ == 'OK':
                num_messages = int(data[0])
                print(f"  ✅ INBOX has {num_messages} messages")
            
            M.logout()
            return True
    
    except imaplib.IMAP4.error as e:
        # This is the specific auth error
        error_msg = str(e)
        print(f"  ❌ IMAP Auth Error: {error_msg}")
        
        # If it's an auth error, try alternative
        if "AUTHENTICATIONFAILED" in error_msg:
            print("\n  Trying with quotes in password...")
            try:
                M = imaplib.IMAP4_SSL('imap.hostinger.com', 993)
                # Try with quoted password
                M.login(USERNAME, f'"{PASSWORD}"')
                print("  ✅ SUCCESS with quoted password!")
                M.logout()
                return True
            except:
                pass
                
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

def test_smtp_simple():
    """Simplest possible SMTP test"""
    print("\nTesting SMTP (simplest method)...")
    
    try:
        print(f"  Connecting to smtp.hostinger.com:465...")
        server = smtplib.SMTP_SSL('smtp.hostinger.com', 465)
        
        print(f"  Logging in as {USERNAME}...")
        server.login(USERNAME, PASSWORD)
        
        print("  ✅ SMTP LOGIN SUCCESSFUL!")
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        error_code, error_msg = e.args
        print(f"  ❌ SMTP Auth Error ({error_code}): {error_msg.decode() if isinstance(error_msg, bytes) else error_msg}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

def test_alternative_ports():
    """Test alternative ports that might work"""
    print("\nTesting alternative configurations...")
    
    # Alternative IMAP ports
    imap_ports = [993, 143]
    for port in imap_ports:
        print(f"\n  Trying IMAP port {port}...")
        try:
            if port == 993:
                M = imaplib.IMAP4_SSL('imap.hostinger.com', port)
            else:
                M = imaplib.IMAP4('imap.hostinger.com', port)
                M.starttls()
            
            M.login(USERNAME, PASSWORD)
            print(f"    ✅ Port {port} works!")
            M.logout()
            return True
        except:
            print(f"    ❌ Port {port} failed")
    
    # Alternative SMTP ports
    smtp_ports = [465, 587, 25]
    for port in smtp_ports:
        print(f"\n  Trying SMTP port {port}...")
        try:
            if port == 465:
                server = smtplib.SMTP_SSL('smtp.hostinger.com', port)
            else:
                server = smtplib.SMTP('smtp.hostinger.com', port)
                if port == 587:
                    server.starttls()
            
            server.login(USERNAME, PASSWORD)
            print(f"    ✅ Port {port} works!")
            server.quit()
            return True
        except:
            print(f"    ❌ Port {port} failed")
    
    return False

def main():
    """Run all tests"""
    
    # Test with simplest methods
    imap_works = test_imap_simple()
    smtp_works = test_smtp_simple()
    
    # If both failed, try alternatives
    if not imap_works and not smtp_works:
        print("\n" + "=" * 60)
        print("Standard ports failed. Testing alternatives...")
        print("=" * 60)
        test_alternative_ports()
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if imap_works or smtp_works:
        print("✅ Authentication is working!")
        print("\nThe credentials are correct. Any issues are with the SSL/TLS configuration.")
    else:
        print("❌ Authentication failed with all methods")
        print("\nSince these credentials work in your email client:")
        print("1. The server might require a specific auth mechanism")
        print("2. The server might have IP-based restrictions")
        print("3. Python's SSL implementation might be incompatible")
        print("\nWorkaround: Use app-specific password if available")

if __name__ == "__main__":
    # Show exact credentials being tested
    print(f"Username: {USERNAME}")
    print(f"Password: {'*' * (len(PASSWORD) - 2)}{PASSWORD[-2:]}")
    print()
    
    main()