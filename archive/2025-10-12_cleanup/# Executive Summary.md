# Executive Summary

## Overview

Email Management Tool is a production-ready Python Flask application for secure, local email interception, moderation, and management. It lets organizations and power users review, edit, and control inbound email before delivery, adding a robust security and compliance layer for sensitive environments. It runs entirely on Windows with SQLite—no cloud dependencies and no Docker required.

---

## Core Purpose

**Email Management Tool** is a production-ready Python Flask application designed for secure email interception, moderation, and management. The tool runs locally on Windows, but it can intercept and moderate emails from both local and remote accounts, as long as you provide valid user-level credentials (username and password/app password). This enables organizations and power users to review, edit, and control inbound email before delivery, providing a robust security and compliance layer for sensitive environments. The app runs entirely on Windows with SQLite—no cloud dependencies, no Docker required.
- Moderate and hold suspicious or policy-violating messages for admin review
- Manage multiple accounts (Gmail, Hostinger, Outlook, Yahoo, generic IMAP/SMTP)
- Provide a secure, modern dashboard for all moderation and account management tasks

---

The Email Management Tool is engineered to intercept, moderate, and control inbound email using only standard user credentials (username and password/app password). No admin or elevated privileges are required. The interception works for any email account—local or remote—where you have valid credentials. This is accomplished through:

| Layer         | Technology                 | Details                                   |
|--------------|----------------------------|-------------------------------------------|
**1. SMTP Proxy (Transparent Interception)**

- The tool runs a local SMTP proxy server (using `aiosmtpd`) on `localhost:8587`.
- Email accounts—whether hosted locally or remotely—are configured to forward or deliver inbound mail to this proxy (via account settings or mail routing rules).
- The proxy receives emails before they reach the user’s inbox, parses and stores them, and holds them for moderation.
- Recipients are unaware of this process, as the proxy acts as a transparent relay.
| UI/UX         | Bootstrap 5.3, Custom CSS  | Dark theme, toast notifications, modals    |
| Email         | aiosmtpd, IMAPClient       | SMTP proxy, IMAP monitoring, smart detect  |
| Testing       | pytest                     | Modular test suite, security validation    |

**2. IMAP Monitoring (User-Level Access)**

- The tool uses `IMAPClient` to connect to each email account (local or remote) with only the provided credentials.
- It leverages IMAP’s `IDLE` command to monitor for new messages in real time.
- When a new message arrives, it is moved to a "Quarantine" folder or copied and deleted from the inbox using standard IMAP operations.
- No admin access is required; all actions use permitted user-level IMAP commands.

## Key Features and Methods

This approach allows for effective email interception and moderation using only user-level credentials, regardless of where the email account is hosted. It is suitable for various use cases where administrative access may not be available or desirable.

#### 1) SMTP Proxy (Transparent Interception)

- Runs a local SMTP proxy server (aiosmtpd) on localhost:8587.
- Email accounts are configured to direct inbound mail to this proxy (forwarding or routing rules).
- The proxy receives emails before they reach the user’s inbox, parses and stores them, and holds them for moderation.
- Recipients are unaware, as the proxy acts as a transparent relay.

Example (Python):

```python
from aiosmtpd.controller import Controller
from app.services.interception import process_incoming_email

class InterceptHandler:
    async def handle_DATA(self, server, session, envelope):
        raw_email = envelope.content
        process_incoming_email(raw_email)
        return '250 Message intercepted and pending review.'

controller = Controller(InterceptHandler(), hostname='localhost', port=8587)
controller.start()
```

#### 2) IMAP Monitoring (User-Level Access)

- Uses IMAPClient to connect to each account with the provided credentials.
- Leverages IMAP IDLE to detect new messages in near real time.
- New messages are moved to a Quarantine folder, or copied and deleted from the inbox using standard IMAP operations.

Example (Python):

```python
from imapclient import IMAPClient

def quarantine_new_messages(host, username, password):
    with IMAPClient(host) as client:
        client.login(username, password)
        client.select_folder('INBOX')
        for uid, data in client.idle_check(timeout=30):
            client.move([uid], 'Quarantine')
```

#### 3) Moderation and Release (Invisible to Recipients)

- Held messages are reviewed in the dashboard.
- Admins can edit, release (append to INBOX), or discard messages.
- Released messages are delivered to the inbox using IMAP APPEND, preserving timestamps and metadata.

Example (Python):

```python
def release_message(client, raw_email, internaldate):
    client.append('INBOX', raw_email, flags=['\\Seen'], msg_time=internaldate)
```

#### 4) Audit Logging and Security

- All actions (intercept, edit, release, discard) are logged in SQLite for compliance.
- Credentials are encrypted at rest.
- Rate limiting and CSRF protection are enforced at the application layer.

---

## How It Works (Summary)

- SMTP Proxy: local proxy at localhost:8587 receives email before the real inbox, parses and stores for moderation.
- IMAP Monitoring: connects with user credentials, uses IDLE to detect new messages and moves them to Quarantine.
- Moderation and Release: messages are edited/released/discarded; releases use IMAP APPEND so recipients only see the final moderated message.

---

## Design Rationale and Best Practices

- Modular Design: Flask blueprints and clear service boundaries.
- Security Measures: CSRF protection, rate limiting, bcrypt for password hashing.
- Encryption: Symmetric encryption (Fernet) for stored credentials.
- Testing: pytest-based suite for interception, security, and functional flows.
- Error Handling: resilient error paths around SMTP/IMAP failures and transient connectivity.
- Scalability Considerations: for larger deployments, consider PostgreSQL or another scalable database.
- UX: user-friendly dashboard with consistent styling and non-blocking notifications.

---

## Security and Compliance

- Audit Trail: every action is logged for compliance and investigation.
- Principle of Least Privilege: operates with standard user credentials only.
- Local-Only Operation: no cloud dependencies; suitable for sensitive environments.

---

## User Experience

- Responsive dashboard for desktop, tablet, and mobile
- Non-blocking notifications (Bootstrap toasts)
- Consistent input and card styling for clarity and accessibility

---

## Supported Providers

- Gmail: App Password, STARTTLS/SSL, IMAP
- Hostinger: Direct SSL, IMAP
- Outlook/Yahoo: App Password, IMAP
- Generic: any IMAP/SMTP provider with smart detection

---

## Deployment and Operations

- Runs locally on Windows; no external dependencies
- Automated security setup via PowerShell
- Easy account management via dashboard or scripts
- Comprehensive test suite for interception, stats, and security

---

## Why Use This Tool?

- Prevent data leaks and policy violations before email delivery
- Centralize email moderation across multiple accounts
- Maintain full control and auditability over inbound communications
- Deploy securely in sensitive environments with no cloud exposure

---

## References

- Technical details: [docs/INTERCEPTION_IMPLEMENTATION.md](docs/INTERCEPTION_IMPLEMENTATION.md)
- Style guide: [docs/STYLEGUIDE.md](docs/STYLEGUIDE.md)