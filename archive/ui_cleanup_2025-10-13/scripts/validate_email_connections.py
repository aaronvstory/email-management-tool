#!/usr/bin/env python3
"""
Email Connection Validation Script
Tests IMAP/SMTP connections with real credentials to ensure validation is production-ready
NO FAKE VALIDATION - All tests use actual network connections

Credentials are loaded from environment (.env supported). If vars are missing,
the corresponding tests are skipped with a clear message.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.email_helpers import test_email_connection

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ANSI colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text):
    """Print formatted section header"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(70)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


def print_test(test_name, expected_result):
    """Print test info"""
    print(f"\n{BOLD}TEST: {test_name}{RESET}")
    print(f"Expected: {expected_result}")
    print(f"{'-'*70}")


def map_friendly(msg: str) -> str:
    lower = (msg or "").lower()
    if "authenticationfailed" in lower or "username and password are required" in lower:
        return "Incorrect or missing credentials"
    if "getaddrinfo failed" in lower or "name or service not known" in lower or "nodename nor servname provided" in lower:
        return "Server not found. Check hostname."
    if "timed out" in lower or "timeout" in lower:
        return "Connection timed out. Check firewall or port."
    if "ssl" in lower and "wrong version number" in lower:
        return "SSL/TLS mismatch. Verify port and SSL setting."
    return msg


def run_test(kind, host, port, username, password, use_ssl, should_succeed):
    """
    Run connection test and validate result matches expectations

    Returns:
        bool: True if test passed (result matches expectation)
    """
    success, message = test_email_connection(kind, host, port, username, password, use_ssl)

    if success == should_succeed:
        status = f"{GREEN}✅ PASS{RESET}"
        result = f"Got expected result: {'SUCCESS' if success else 'FAILURE'}"
    else:
        status = f"{RED}❌ FAIL{RESET}"
        result = f"Expected {'SUCCESS' if should_succeed else 'FAILURE'}, got {'SUCCESS' if success else 'FAILURE'}"

    print(f"{status} - {result}")
    print(f"Message: {map_friendly(message)}")

    return success == should_succeed


def main():
    print_header("EMAIL CONNECTION VALIDATION - PRODUCTION READINESS TEST")

    print(f"{BOLD}Purpose:{RESET} Verify that email connection validation is 100% real")
    print(f"{BOLD}Method:{RESET} Test known-good and known-bad credentials against real servers")
    print(f"{BOLD}Success Criteria:{RESET} All tests must match expected results\n")

    all_passed = True
    test_results = []

    # Pull creds from environment
    # Support multiple env naming schemes
    GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS') or os.getenv('GMAIL_EMAIL')
    GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD') or os.getenv('GMAIL_APP_PASSWORD')
    HOSTINGER_ADDRESS = os.getenv('HOSTINGER_ADDRESS') or os.getenv('HOSTINGER_EMAIL')
    HOSTINGER_PASSWORD = os.getenv('HOSTINGER_PASSWORD')

    # ===========================================
    # SECTION 1: Known GOOD credentials
    # ===========================================
    print_header("SECTION 1: VALID CREDENTIALS (Should SUCCEED)")

    if GMAIL_ADDRESS and GMAIL_PASSWORD:
        # Test 1: Gmail IMAP (known good)
        print_test(
            "Gmail IMAP - Primary Test Account",
            "SUCCESS - Real IMAP connection to Gmail"
        )
        passed = run_test(
            kind='imap',
            host='imap.gmail.com',
            port=993,
            username=GMAIL_ADDRESS,
            password=GMAIL_PASSWORD,
            use_ssl=True,
            should_succeed=True
        )
        all_passed = all_passed and passed
        test_results.append(("Gmail IMAP (valid)", passed))
    else:
        print(f"{YELLOW}Skipping Gmail IMAP valid test: set GMAIL_ADDRESS and GMAIL_PASSWORD in .env{RESET}")

    if GMAIL_ADDRESS and GMAIL_PASSWORD:
        # Test 2: Gmail SMTP (known good)
        print_test(
            "Gmail SMTP - Port 587 STARTTLS",
            "SUCCESS - Real SMTP connection with STARTTLS"
        )
        passed = run_test(
            kind='smtp',
            host='smtp.gmail.com',
            port=587,
            username=GMAIL_ADDRESS,
            password=GMAIL_PASSWORD,
            use_ssl=False,
            should_succeed=True
        )
        all_passed = all_passed and passed
        test_results.append(("Gmail SMTP (valid)", passed))
    else:
        print(f"{YELLOW}Skipping Gmail SMTP valid test: set GMAIL_ADDRESS and GMAIL_PASSWORD in .env{RESET}")

    if HOSTINGER_ADDRESS and HOSTINGER_PASSWORD:
        # Test 3: Hostinger IMAP (known good)
        print_test(
            "Hostinger IMAP - Secondary Test Account",
            "SUCCESS - Real IMAP connection to Hostinger"
        )
        passed = run_test(
            kind='imap',
            host='imap.hostinger.com',
            port=993,
            username=HOSTINGER_ADDRESS,
            password=HOSTINGER_PASSWORD,
            use_ssl=True,
            should_succeed=True
        )
        all_passed = all_passed and passed
        test_results.append(("Hostinger IMAP (valid)", passed))
    else:
        print(f"{YELLOW}Skipping Hostinger IMAP valid test: set HOSTINGER_ADDRESS and HOSTINGER_PASSWORD in .env{RESET}")

    if HOSTINGER_ADDRESS and HOSTINGER_PASSWORD:
        # Test 4: Hostinger SMTP (known good)
        print_test(
            "Hostinger SMTP - Port 465 Direct SSL",
            "SUCCESS - Real SMTP connection with direct SSL"
        )
        passed = run_test(
            kind='smtp',
            host='smtp.hostinger.com',
            port=465,
            username=HOSTINGER_ADDRESS,
            password=HOSTINGER_PASSWORD,
            use_ssl=True,
            should_succeed=True
        )
        all_passed = all_passed and passed
        test_results.append(("Hostinger SMTP (valid)", passed))
    else:
        print(f"{YELLOW}Skipping Hostinger SMTP valid test: set HOSTINGER_ADDRESS and HOSTINGER_PASSWORD in .env{RESET}")

    # ===========================================
    # SECTION 2: Known BAD credentials
    # ===========================================
    print_header("SECTION 2: INVALID CREDENTIALS (Should FAIL)")

    if GMAIL_ADDRESS:
        # Test 5: Gmail IMAP with wrong password
        print_test(
            "Gmail IMAP - Wrong Password",
            "FAILURE - Authentication should fail"
        )
        passed = run_test(
            kind='imap',
            host='imap.gmail.com',
            port=993,
            username=GMAIL_ADDRESS,
            password='wrong_password_12345',
            use_ssl=True,
            should_succeed=False
        )
        all_passed = all_passed and passed
        test_results.append(("Gmail IMAP (invalid password)", passed))
    else:
        print(f"{YELLOW}Skipping Gmail IMAP invalid password test: set GMAIL_ADDRESS in .env{RESET}")

    if GMAIL_ADDRESS:
        # Test 6: Gmail SMTP with wrong password
        print_test(
            "Gmail SMTP - Wrong Password",
            "FAILURE - Authentication should fail"
        )
        passed = run_test(
            kind='smtp',
            host='smtp.gmail.com',
            port=587,
            username=GMAIL_ADDRESS,
            password='wrong_password_12345',
            use_ssl=False,
            should_succeed=False
        )
        all_passed = all_passed and passed
        test_results.append(("Gmail SMTP (invalid password)", passed))
    else:
        print(f"{YELLOW}Skipping Gmail SMTP invalid password test: set GMAIL_ADDRESS in .env{RESET}")

    # Test 7: Non-existent IMAP server
    print_test(
        "Non-existent IMAP Server",
        "FAILURE - Server should not exist"
    )
    passed = run_test(
        kind='imap',
        host='imap.this-server-does-not-exist-12345.com',
        port=993,
        username='fake@example.com',
        password='fake',
        use_ssl=True,
        should_succeed=False
    )
    all_passed = all_passed and passed
    test_results.append(("Non-existent IMAP server", passed))

    # Test 8: Wrong port number
    print_test(
        "Gmail IMAP - Wrong Port (995 is POP3, not IMAP)",
        "FAILURE - Wrong port should fail or timeout"
    )
    passed = run_test(
        kind='imap',
        host='imap.gmail.com',
        port=995,  # POP3 port, not IMAP
        username='ndayijecika@gmail.com',
        password='bjormgplhgwkgpad',
        use_ssl=True,
        should_succeed=False
    )
    all_passed = all_passed and passed
    test_results.append(("Gmail IMAP (wrong port)", passed))

    # Test 9: Missing required parameters
    print_test(
        "Missing Host Parameter",
        "FAILURE - Missing parameters should fail validation"
    )
    passed = run_test(
        kind='imap',
        host='',  # Empty host
        port=993,
        username='test@example.com',
        password='test',
        use_ssl=True,
        should_succeed=False
    )
    all_passed = all_passed and passed
    test_results.append(("Missing host parameter", passed))

    # ===========================================
    # SECTION 3: Edge cases
    # ===========================================
    print_header("SECTION 3: EDGE CASES")

    if GMAIL_ADDRESS:
        # Test 10: Empty password should fail fast
        print_test(
            "Empty Password (Gmail IMAP)",
            "FAILURE - Missing password should be rejected"
        )
        passed = run_test(
            kind='imap',
            host='imap.gmail.com',
            port=993,
            username=GMAIL_ADDRESS,
            password='',
            use_ssl=True,
            should_succeed=False
        )
        all_passed = all_passed and passed
        test_results.append(("Empty password", passed))
    else:
        print(f"{YELLOW}Skipping empty password test: set GMAIL_ADDRESS in .env{RESET}")

    if GMAIL_ADDRESS and GMAIL_PASSWORD:
        # Misconfiguration: 587 with SSL=True should still succeed (STARTTLS)
        print_test(
            "Gmail SMTP - Port 587 with SSL=True",
            "SUCCESS - Should negotiate STARTTLS"
        )
        passed = run_test(
            kind='smtp',
            host='smtp.gmail.com',
            port=587,
            username=GMAIL_ADDRESS,
            password=GMAIL_PASSWORD,
            use_ssl=True,
            should_succeed=True
        )
        all_passed = all_passed and passed
        test_results.append(("Gmail SMTP (587 + SSL=True)", passed))

        # Misconfiguration: 465 with SSL=False should succeed (we force SSL on 465)
        print_test(
            "Gmail SMTP - Port 465 with SSL=False",
            "SUCCESS - Should force direct SSL on 465"
        )
        passed = run_test(
            kind='smtp',
            host='smtp.gmail.com',
            port=465,
            username=GMAIL_ADDRESS,
            password=GMAIL_PASSWORD,
            use_ssl=False,
            should_succeed=True
        )
        all_passed = all_passed and passed
        test_results.append(("Gmail SMTP (465 + SSL=False)", passed))

    # ===========================================
    # FINAL REPORT
    # ===========================================
    print_header("VALIDATION RESULTS SUMMARY")

    print(f"\n{BOLD}Individual Test Results:{RESET}")
    for test_name, passed in test_results:
        status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
        print(f"  {status}  {test_name}")

    passed_count = sum(1 for _, p in test_results if p)
    total_count = len(test_results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print(f"\n{BOLD}Statistics:{RESET}")
    print(f"  Total Tests: {total_count}")
    print(f"  Passed: {passed_count}")
    print(f"  Failed: {total_count - passed_count}")
    print(f"  Pass Rate: {pass_rate:.1f}%")

    print(f"\n{BOLD}Overall Status:{RESET}")
    if all_passed:
        print(f"{GREEN}{BOLD}✅ ALL TESTS PASSED - VALIDATION IS 100% REAL{RESET}")
        print(f"{GREEN}The connection validation system is production-ready.{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}❌ SOME TESTS FAILED - VALIDATION HAS ISSUES{RESET}")
        print(f"{RED}Review failed tests above and fix validation logic.{RESET}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Validation interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}{BOLD}FATAL ERROR:{RESET} {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
