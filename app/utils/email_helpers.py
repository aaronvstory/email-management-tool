"""
Email Helper Utilities
Consolidated email detection and connection testing functions
Phase 3: Helper Consolidation - Extracted from simple_app.py and app/routes/accounts.py
"""

import smtplib
import imaplib
from typing import Tuple


def detect_email_settings(email_address: str) -> dict:
    """
    Smart detection of SMTP/IMAP settings based on email domain.
    Returns dict with smtp_host, smtp_port, smtp_use_ssl, imap_host, imap_port, imap_use_ssl

    Args:
        email_address: Email address to detect settings for

    Returns:
        Dictionary with SMTP and IMAP configuration
    """
    domain = email_address.split('@')[-1].lower() if '@' in email_address else ''

    # Known provider configurations
    providers = {
        'gmail.com': {
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_use_ssl': False,  # STARTTLS on 587
            'imap_host': 'imap.gmail.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'corrinbox.com': {
            'smtp_host': 'smtp.hostinger.com',
            'smtp_port': 465,
            'smtp_use_ssl': True,  # Direct SSL on 465
            'imap_host': 'imap.hostinger.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'outlook.com': {
            'smtp_host': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'smtp_use_ssl': False,
            'imap_host': 'outlook.office365.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'hotmail.com': {
            'smtp_host': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'smtp_use_ssl': False,
            'imap_host': 'outlook.office365.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'yahoo.com': {
            'smtp_host': 'smtp.mail.yahoo.com',
            'smtp_port': 465,
            'smtp_use_ssl': True,
            'imap_host': 'imap.mail.yahoo.com',
            'imap_port': 993,
            'imap_use_ssl': True
        }
    }

    # Return provider settings or generic defaults
    if domain in providers:
        return providers[domain]
    else:
        # Generic defaults - try common patterns
        return {
            'smtp_host': f'smtp.{domain}',
            'smtp_port': 587,
            'smtp_use_ssl': False,
            'imap_host': f'imap.{domain}',
            'imap_port': 993,
            'imap_use_ssl': True
        }


def test_email_connection(kind: str, host: str, port: int, username: str, password: str, use_ssl: bool) -> Tuple[bool, str]:
    """
    Lightweight connectivity test for IMAP/SMTP.
    Returns (success, message). Avoids introducing heavy network timeouts.

    Args:
        kind: 'imap' or 'smtp'
        host: Server hostname
        port: Server port
        username: Authentication username
        password: Authentication password
        use_ssl: Whether to use SSL/TLS

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not host or not port or not username:
        return False, "Missing connection parameters"

    try:
        if kind.lower() == 'imap':
            if use_ssl:
                client = imaplib.IMAP4_SSL(host, int(port))
            else:
                client = imaplib.IMAP4(host, int(port))
            if password:
                client.login(username, password)
            client.logout()
            return True, f"IMAP OK {host}:{port}"

        if kind.lower() == 'smtp':
            if use_ssl and int(port) in (465, 587):
                if int(port) == 465:
                    server = smtplib.SMTP_SSL(host, int(port), timeout=10)
                else:
                    server = smtplib.SMTP(host, int(port), timeout=10)
                    server.starttls()
            else:
                server = smtplib.SMTP(host, int(port), timeout=10)
            if password:
                server.login(username, password)
            server.quit()
            return True, f"SMTP OK {host}:{port}"

        return False, f"Unsupported kind {kind}"

    except Exception as e:
        return False, str(e)
