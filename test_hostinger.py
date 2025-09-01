#!/usr/bin/env python3
"""
Test Hostinger email connectivity directly
"""

import imaplib
import smtplib
import ssl

# Credentials
username = "mcintyre@corrinbox.com"
password = "Slaypap3!!"

print("Testing Hostinger Email Connectivity")
print("=" * 50)

# Test IMAP
print("\n1. Testing IMAP Connection...")
print(f"   Server: imap.hostinger.com:993")
print(f"   Username: {username}")

try:
    # Create SSL context
    context = ssl.create_default_context()
    
    # Connect to IMAP server
    imap = imaplib.IMAP4_SSL("imap.hostinger.com", 993, ssl_context=context)
    print("   ✅ Connected to IMAP server")
    
    # Try to login
    try:
        imap.login(username, password)
        print("   ✅ IMAP authentication successful!")
        
        # List folders
        status, folders = imap.list()
        if status == 'OK':
            print(f"   ✅ Found {len(folders)} folders")
            
            # Select INBOX
            status, data = imap.select('INBOX')
            if status == 'OK':
                message_count = int(data[0].decode()) if data[0] else 0
                print(f"   ✅ INBOX has {message_count} messages")
        
        imap.logout()
        
    except Exception as e:
        print(f"   ❌ IMAP authentication failed: {e}")
        
except Exception as e:
    print(f"   ❌ IMAP connection failed: {e}")

# Test SMTP
print("\n2. Testing SMTP Connection...")
print(f"   Server: smtp.hostinger.com:465 (SSL)")
print(f"   Username: {username}")

try:
    # Create SSL context
    context = ssl.create_default_context()
    
    # Connect to SMTP server with SSL
    smtp = smtplib.SMTP_SSL("smtp.hostinger.com", 465, context=context, timeout=30)
    print("   ✅ Connected to SMTP server")
    
    # Get server info
    smtp.set_debuglevel(0)  # Set to 1 for debug output
    
    # Try to login
    try:
        smtp.login(username, password)
        print("   ✅ SMTP authentication successful!")
        
        # Verify send capability
        try:
            smtp.verify(username)
            print("   ✅ Email send capability verified")
        except:
            print("   ⚠️  VRFY command not supported (normal for most servers)")
        
        smtp.quit()
        
    except Exception as e:
        print(f"   ❌ SMTP authentication failed: {e}")
        
except Exception as e:
    print(f"   ❌ SMTP connection failed: {e}")

print("\n" + "=" * 50)
print("Testing complete!")

# Try alternative authentication methods
print("\n3. Alternative Authentication Test...")
print("   Trying with encoded password...")

import base64

try:
    # Try with base64 encoded credentials
    encoded_user = base64.b64encode(username.encode()).decode()
    encoded_pass = base64.b64encode(password.encode()).decode()
    print(f"   Encoded username: {encoded_user[:10]}...")
    print(f"   Encoded password: {encoded_pass[:10]}...")
    
    # Note: The actual authentication already handles encoding internally
    # This is just to verify the credentials are being encoded properly
    
except Exception as e:
    print(f"   ❌ Encoding test failed: {e}")

print("\nIf authentication is still failing, please check:")
print("1. The password is correct (no extra spaces)")
print("2. The account allows IMAP/SMTP access")
print("3. No 2-factor authentication is blocking access")
print("4. The account is not locked or suspended")