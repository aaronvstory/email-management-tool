#!/usr/bin/env python3
"""
Debug Hostinger email authentication with multiple methods
"""

import imaplib
import smtplib
import ssl
import socket
import sys

# Credentials - CONFIRMED WORKING IN EMAIL CLIENT
username = "mcintyre@corrinbox.com"
password = "Slaypap3!!"  # Note: Two exclamation marks

print("=" * 70)
print("HOSTINGER EMAIL AUTHENTICATION DEBUGGER")
print("=" * 70)
print(f"Username: {username}")
print(f"Password: {'*' * (len(password)-2) + password[-2:]}")  # Show last 2 chars
print("=" * 70)

def test_imap_methods():
    """Test different IMAP connection methods"""
    print("\n🔍 TESTING IMAP CONNECTIONS (imap.hostinger.com:993)")
    print("-" * 50)
    
    # Method 1: Standard SSL connection
    print("\n1. Standard IMAP4_SSL connection:")
    try:
        imap = imaplib.IMAP4_SSL("imap.hostinger.com", 993)
        print("   ✅ Connected to IMAP server")
        
        try:
            result = imap.login(username, password)
            print(f"   ✅ LOGIN SUCCESSFUL! Result: {result}")
            
            # Get some info
            status, folders = imap.list()
            if status == 'OK':
                print(f"   ✅ Found {len(folders)} folders")
            
            imap.logout()
            return True
            
        except Exception as e:
            print(f"   ❌ Login failed: {e}")
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
    
    # Method 2: With custom SSL context (less strict)
    print("\n2. IMAP with custom SSL context (less strict):")
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        imap = imaplib.IMAP4_SSL("imap.hostinger.com", 993, ssl_context=context)
        print("   ✅ Connected to IMAP server")
        
        try:
            result = imap.login(username, password)
            print(f"   ✅ LOGIN SUCCESSFUL! Result: {result}")
            imap.logout()
            return True
            
        except Exception as e:
            print(f"   ❌ Login failed: {e}")
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
    
    # Method 3: Using raw socket with SSL wrap
    print("\n3. Raw socket with SSL wrap:")
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        # Wrap with SSL
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        wrapped_socket = context.wrap_socket(sock, server_hostname="imap.hostinger.com")
        wrapped_socket.connect(("imap.hostinger.com", 993))
        print("   ✅ Raw SSL connection established")
        
        # Read greeting
        data = wrapped_socket.recv(1024)
        print(f"   Server greeting: {data.decode()[:50]}...")
        
        # Try LOGIN command
        login_cmd = f'A001 LOGIN "{username}" "{password}"\r\n'
        wrapped_socket.send(login_cmd.encode())
        response = wrapped_socket.recv(1024)
        print(f"   Login response: {response.decode()}")
        
        if b'OK' in response:
            print("   ✅ LOGIN SUCCESSFUL via raw socket!")
            wrapped_socket.close()
            return True
        else:
            print("   ❌ Login failed via raw socket")
            
        wrapped_socket.close()
        
    except Exception as e:
        print(f"   ❌ Raw socket failed: {e}")
    
    return False

def test_smtp_methods():
    """Test different SMTP connection methods"""
    print("\n🔍 TESTING SMTP CONNECTIONS (smtp.hostinger.com:465)")
    print("-" * 50)
    
    # Method 1: Standard SMTP_SSL
    print("\n1. Standard SMTP_SSL connection:")
    try:
        smtp = smtplib.SMTP_SSL("smtp.hostinger.com", 465, timeout=30)
        smtp.set_debuglevel(0)
        print("   ✅ Connected to SMTP server")
        
        try:
            result = smtp.login(username, password)
            print(f"   ✅ LOGIN SUCCESSFUL! Result: {result}")
            smtp.quit()
            return True
            
        except Exception as e:
            print(f"   ❌ Login failed: {e}")
            try:
                smtp.quit()
            except:
                pass
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
    
    # Method 2: With custom SSL context
    print("\n2. SMTP with custom SSL context (less strict):")
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        smtp = smtplib.SMTP_SSL("smtp.hostinger.com", 465, context=context, timeout=30)
        print("   ✅ Connected to SMTP server")
        
        try:
            result = smtp.login(username, password)
            print(f"   ✅ LOGIN SUCCESSFUL! Result: {result}")
            smtp.quit()
            return True
            
        except Exception as e:
            print(f"   ❌ Login failed: {e}")
            try:
                smtp.quit()
            except:
                pass
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
    
    # Method 3: Try STARTTLS on port 587 (if available)
    print("\n3. Testing STARTTLS on port 587:")
    try:
        smtp = smtplib.SMTP("smtp.hostinger.com", 587, timeout=30)
        print("   ✅ Connected to SMTP server on port 587")
        
        smtp.ehlo()
        smtp.starttls()
        print("   ✅ STARTTLS successful")
        
        try:
            result = smtp.login(username, password)
            print(f"   ✅ LOGIN SUCCESSFUL! Result: {result}")
            smtp.quit()
            return True
            
        except Exception as e:
            print(f"   ❌ Login failed: {e}")
            try:
                smtp.quit()
            except:
                pass
            
    except Exception as e:
        print(f"   ❌ Port 587 not available or STARTTLS failed: {e}")
    
    return False

def test_password_variations():
    """Test if password encoding is the issue"""
    print("\n🔍 TESTING PASSWORD VARIATIONS")
    print("-" * 50)
    
    passwords_to_try = [
        ("Original", password),
        ("Without last !", password[:-1]),
        ("Escaped", password.replace("!", "\\!")),
        ("URL encoded", password.replace("!", "%21")),
    ]
    
    for desc, pwd in passwords_to_try:
        print(f"\nTrying: {desc} - {'*' * (len(pwd)-2) + pwd[-2:]}")
        
        try:
            imap = imaplib.IMAP4_SSL("imap.hostinger.com", 993)
            try:
                result = imap.login(username, pwd)
                print(f"   ✅ SUCCESS with {desc}! Password that works: {pwd}")
                imap.logout()
                return pwd
            except Exception as e:
                print(f"   ❌ Failed: {str(e)[:50]}")
        except:
            pass
    
    return None

def main():
    """Run all tests"""
    
    # Test IMAP
    imap_success = test_imap_methods()
    
    # Test SMTP
    smtp_success = test_smtp_methods()
    
    # If both failed, try password variations
    if not imap_success and not smtp_success:
        print("\n⚠️  Standard methods failed. Testing password variations...")
        working_pwd = test_password_variations()
        
        if working_pwd:
            print(f"\n✅ FOUND WORKING PASSWORD: {working_pwd}")
            print("Update your .env file with this password!")
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    if imap_success or smtp_success:
        print("✅ Authentication successful!")
        print("\nThe issue was likely with:")
        print("- SSL certificate verification")
        print("- Connection method")
        print("\nSolution: Update the email_diagnostics.py to use the working method")
    else:
        print("❌ All authentication methods failed")
        print("\nPossible issues:")
        print("1. Account requires app-specific password")
        print("2. Account has IP restrictions")
        print("3. IMAP/SMTP not enabled for this account")
        print("4. Account is using 2-factor authentication")
        print("\nNext steps:")
        print("1. Verify these exact credentials work in your email client")
        print("2. Check Hostinger account settings for security restrictions")
        print("3. Contact Hostinger support for IMAP/SMTP requirements")

if __name__ == "__main__":
    main()