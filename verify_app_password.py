#!/usr/bin/env python3
"""
Gmail App Password Verification Helper
Helps you test the correct format of your App Password
"""

import smtplib

def test_password(password):
    """Test a specific password format"""
    print(f"\nTesting password: {password}")
    print(f"Length: {len(password)} characters")
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login('ndayijecika@gmail.com', password)
        print("✅ SUCCESS! This password works!")
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

print("="*60)
print("GMAIL APP PASSWORD VERIFICATION")
print("="*60)
print("\nYour App Password: 'juzk lyge ugjo jalr'")
print("\nTesting different format variations...")

# Test different possible formats
passwords_to_test = [
    "juzklygeugojalr",     # All lowercase, no spaces
    "juzklygeugjojair",    # Alternative interpretation
    "juzk lyge ugjo jalr", # With spaces (unlikely to work)
    "JUZKLYGEUGOJALR",     # All uppercase
]

success = False
for pwd in passwords_to_test:
    if test_password(pwd):
        success = True
        print(f"\n✅ FOUND WORKING FORMAT: {pwd}")
        print(f"Use this in your configuration files!")
        break

if not success:
    print("\n" + "="*60)
    print("❌ None of the password formats worked.")
    print("\nPOSSIBLE ISSUES:")
    print("1. The App Password might be typed incorrectly")
    print("2. The App Password might have been revoked")
    print("3. 2FA might not be properly enabled")
    print("\n✅ SOLUTION:")
    print("1. Go to https://myaccount.google.com/apppasswords")
    print("2. Delete any existing App Passwords")
    print("3. Generate a NEW App Password")
    print("4. Copy it EXACTLY as shown (usually 16 lowercase letters)")
    print("5. Remove any spaces when entering it here")
    print("\nThe format should be 16 lowercase letters like: abcdefghijklmnop")

print("\n" + "="*60)
print("MANUAL TEST")
print("="*60)
print("\nYou can also enter your App Password manually to test it:")
print("(Copy and paste the 16-character password from Google)")
print("Press Enter to skip manual testing.")

manual_pwd = input("\nEnter App Password (no spaces): ").strip()
if manual_pwd:
    if test_password(manual_pwd):
        print(f"\n✅ SUCCESS! Update your files with: {manual_pwd}")
    else:
        print("\n❌ This password didn't work either.")
        print("Please generate a new App Password from Google.")