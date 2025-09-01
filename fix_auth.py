#!/usr/bin/env python3
"""
Fix Hostinger authentication - test with exact working credentials
"""

import imaplib
import smtplib
import ssl
import sys

# EXACT credentials that work in email client
username = "mcintyre@corrinbox.com"
password = "Slaypap3!!"

print("Testing with CONFIRMED WORKING credentials")
print("Username:", username)
print("Password length:", len(password), "chars")
print("-" * 50)

# Test 1: IMAP with disabled certificate verification
print("\n1. Testing IMAP (port 993)...")
try:
    # Create SSL context that doesn't verify certificates
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Connect
    imap = imaplib.IMAP4_SSL("imap.hostinger.com", 993, ssl_context=ctx)
    print("   Connected to IMAP server")
    
    # Login
    imap.login(username, password)
    print("   ✅ IMAP LOGIN SUCCESSFUL!")
    
    # Get folder list
    status, folders = imap.list()
    print(f"   Found {len(folders)} folders")
    
    # Select INBOX
    status, data = imap.select("INBOX")
    if status == "OK":
        count = int(data[0])
        print(f"   INBOX has {count} messages")
    
    imap.logout()
    
except imaplib.IMAP4.error as e:
    print(f"   ❌ IMAP login error: {e}")
except Exception as e:
    print(f"   ❌ IMAP error: {e}")

# Test 2: SMTP with disabled certificate verification  
print("\n2. Testing SMTP (port 465)...")
try:
    # Create SSL context that doesn't verify certificates
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Connect
    smtp = smtplib.SMTP_SSL("smtp.hostinger.com", 465, context=ctx)
    print("   Connected to SMTP server")
    
    # Login
    smtp.login(username, password)
    print("   ✅ SMTP LOGIN SUCCESSFUL!")
    
    smtp.quit()
    
except smtplib.SMTPAuthenticationError as e:
    print(f"   ❌ SMTP auth error: {e}")
except Exception as e:
    print(f"   ❌ SMTP error: {e}")

print("\n" + "-" * 50)
print("If authentication still fails, the issue might be:")
print("1. Special characters in password need escaping")
print("2. Hostinger requires specific auth mechanism")
print("3. IP address needs whitelisting")