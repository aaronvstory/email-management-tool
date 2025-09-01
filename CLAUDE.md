# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Email Management Tool is a comprehensive Python Flask application for intercepting, moderating, and managing emails across multiple accounts. It provides a web dashboard for reviewing emails before they're sent, with full audit trails and modification capabilities. The application features real-time IMAP/SMTP monitoring, encrypted credential storage, and a modern responsive UI.

**Current Status**: Production-ready with 3 active email accounts configured and all critical bugs fixed (as of Sept 1, 2025).

## Quick Start Commands

### Starting the Application
```bash
# Primary method - runs on http://localhost:5000
python simple_app.py

# Alternative Windows methods
start.bat                    # Batch file launcher
.\manage.ps1 start          # PowerShell management

# Access points:
# - Web Dashboard: http://localhost:5000
# - SMTP Proxy: localhost:8587
# - Login: admin / admin123
```

### Testing & Validation
```bash
# Test all email account connections
python test_all_connections.py

# Validate all fixes are working
python validate_fixes.py

# Add new Gmail account with app password
python add_gmail_account.py

# Update account credentials interactively
python update_credentials.py

# Run complete email workflow test
python test_complete_workflow.py
```

## High-Level Architecture

### Core Application Structure
```
simple_app.py (1520 lines) - Monolithic Flask application containing:
├── Flask Routes (20+ endpoints)
│   ├── /dashboard - Unified dashboard with tabs
│   ├── /emails - Email queue management
│   ├── /accounts - Email account management
│   ├── /diagnostics - Connection testing
│   └── /api/* - RESTful API endpoints
├── SMTP Proxy Handler
│   └── EmailModerationHandler class using aiosmtpd
├── IMAP Monitoring
│   └── monitor_imap_account() - Per-account threads
├── Database Operations
│   └── SQLite with row_factory for dict access
└── Encryption Layer
    └── Fernet symmetric encryption for credentials
```

### Critical Database Schema
```sql
email_accounts (
    id, account_name, email_address,
    imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
    smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl,
    is_active, last_checked, last_error, created_at, updated_at
)

email_messages (
    id, message_id, sender, recipients, subject, body, raw_email,
    status (PENDING/APPROVED/REJECTED/SENT),
    risk_score, keywords_matched, created_at, updated_at
)
```

### Email Processing Pipeline
1. **SMTP Interception** → Port 8587 captures outgoing emails
2. **Database Storage** → SQLite with encrypted credentials
3. **Risk Assessment** → Keyword matching and scoring
4. **Dashboard Review** → Manual approval/rejection/editing
5. **SMTP Relay** → Approved emails sent via configured relay
6. **IMAP Monitoring** → Parallel threads monitor each account's inbox

### Threading Model
- Main Flask thread (web server)
- SMTP proxy thread (email interception)
- N IMAP monitor threads (one per active account)
- All threads use `daemon=True` for clean shutdown

## Active Email Accounts (Test Credentials)

### Gmail Account 1 - NDayijecika ✅
```
Email: ndayijecika@gmail.com
Password: VDMcQeklCH2mom (Gmail login only)
App Password: gbrw tagu ayhy wtry (WITH SPACES - for IMAP/SMTP)
SMTP: smtp.gmail.com:587 (STARTTLS)
IMAP: imap.gmail.com:993 (SSL)
Status: Active, 133 messages in inbox
```

### Gmail Test Account ✅
```
Email: test.email.manager@gmail.com
App Password: (needs configuration)
SMTP: smtp.gmail.com:587 (STARTTLS)
IMAP: imap.gmail.com:993 (SSL)
```

### Hostinger Account ✅
```
Email: mcintyre@corrinbox.com
Password: Slaypap3!!
SMTP: smtp.hostinger.com:465 (SSL)
IMAP: imap.hostinger.com:993 (SSL)
```

## Project Organization (After Cleanup)

### Active Files Structure
```
Email-Management-Tool/
├── simple_app.py              # Main application (DO NOT DELETE)
├── email_manager.db           # SQLite database
├── key.txt                    # Encryption key (KEEP SECURE)
├── templates/                 # Active templates
│   ├── dashboard_unified.html # Main dashboard
│   ├── accounts_simple.html   # Account management
│   ├── email_queue.html       # Email queue
│   └── add_account.html       # Add account form
├── app/                       # Application modules
└── archive/                   # Archived test results
    ├── test-results/          # Old JSON test results
    └── old-tests/             # Obsolete debug files
```

### Key Files Reference
- **simple_app.py** - Main Flask application
- **populate_test_accounts.py** - Database initialization
- **add_gmail_account.py** - Gmail account helper
- **test_all_connections.py** - Connection tester
- **validate_fixes.py** - Fix validation
- **ORGANIZATION_GUIDE.md** - Complete file inventory

## Recent Fixes & Improvements (Sept 1, 2025)

### Critical Bug Fixes Applied
1. **getaddrinfo() Error** ✅
   - Added `conn.row_factory = sqlite3.Row` throughout
   - Changed from index to dictionary access
   - Convert ports to integers before use

2. **Template Errors** ✅
   - Fixed `'list object' has no attribute 'items'`
   - Added compatibility for both list and dict formats
   - Fixed NoneType replace errors with null checks

3. **Diagnostics Redirect** ✅
   - Fixed redirect logic for account_id parameter
   - Dashboard diagnostics tab now works correctly

### Database Access Pattern (CRITICAL)
```python
# ALWAYS use this pattern for database access:
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # Enable dictionary access
cursor = conn.cursor()
# Use account['field_name'] not account[index]
```

## Common Development Tasks

### Adding a New Email Account
```python
# Use the helper script
python add_gmail_account.py

# Or manually via dashboard:
# 1. Navigate to http://localhost:5000/accounts
# 2. Click "Add New Account"
# 3. For Gmail: Use App Password (with spaces)
# 4. Test with "Test IMAP" and "Test SMTP" buttons
```

### Debugging Connection Issues
```python
# Check schema
python -c "import sqlite3; conn = sqlite3.connect('email_manager.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(email_accounts)'); print(cursor.fetchall())"

# Test specific account
python test_all_connections.py

# Check logs
cat app.log
```

### Gmail Configuration Requirements
1. Enable 2-Factor Authentication
2. Generate App Password at https://myaccount.google.com/apppasswords
3. Use App Password WITH SPACES: `xxxx xxxx xxxx xxxx`
4. Enable IMAP in Gmail settings
5. Use port 587 for SMTP (STARTTLS), 993 for IMAP (SSL)

## Template System

### Active Templates (Use These)
- `dashboard_unified.html` - Main dashboard with tabs
- `accounts_simple.html` - Account management (handles list/dict)
- `email_queue.html` - Email queue with filters
- `add_account.html` - Add account form
- `base.html` - Master template with sidebar

### Template Inheritance
All templates extend `base.html` which provides:
- Bootstrap 5.3 styling
- Sidebar navigation with active states
- User context and role checking
- Flash message handling
- Gradient purple theme (#667eea to #764ba2)

## API Endpoints

### Core Routes
- `GET /` - Login page
- `GET /dashboard` - Main dashboard
- `GET /emails` - Email queue (with status filter)
- `GET /accounts` - Account management
- `POST /accounts/add` - Add new account
- `GET /diagnostics` - Connection testing

### API Endpoints
- `GET /api/stats` - Real-time statistics
- `POST /api/test-connection/<type>` - Test IMAP/SMTP
- `GET /api/diagnostics/<account_id>` - Per-account diagnostics
- `GET /api/accounts/<account_id>/health` - Health status
- `POST /email/<id>/action` - Approve/reject email

## Security Considerations

### Credential Storage
- All passwords encrypted with Fernet
- Key stored in `key.txt` (auto-generated if missing)
- Never commit `key.txt` or `email_manager.db` to git

### Authentication
- Flask-Login for session management
- Bcrypt for password hashing
- Role-based access (admin/user)
- Session timeout after inactivity

## Performance Optimizations

### Database
- SQLite with 10-second timeout for concurrent access
- Row factory for efficient dict access
- Prepared statements prevent SQL injection

### Threading
- Daemon threads for clean shutdown
- Per-account IMAP monitoring
- Non-blocking SMTP proxy

## Troubleshooting Guide

### Common Issues & Solutions

#### "getaddrinfo() argument 1 must be string or None"
- **Fixed**: Ensure row_factory is set and use dictionary access

#### "NoneType object has no attribute 'replace'"
- **Fixed**: Add null checks in templates

#### Gmail Authentication Failed
- Ensure using App Password (not regular password)
- Keep spaces in App Password
- Check 2FA is enabled

#### Port Already in Use
```bash
# Check what's using the port
netstat -an | findstr :8587
# Kill specific process
taskkill /F /PID <pid>
```

## Git Workflow

### Before Major Changes
```bash
git add -A
git commit -m "Checkpoint: Description of current state"
```

### After Cleanup/Organization
```bash
git add -A
git commit -m "Organization: Archived unused files, fixed bugs"
```

## Dependencies (requirements.txt)

Core requirements:
- Flask==3.0.0
- aiosmtpd==1.4.4
- Flask-Login==0.6.3
- cryptography==41.0.7
- python-dotenv==1.0.0

## Future Improvements Roadmap

1. **Database Migration** - Move from SQLite to PostgreSQL for production
2. **WebSocket Support** - Real-time dashboard updates
3. **Email Templates** - Customizable approval/rejection templates
4. **Advanced Rules** - Machine learning for risk scoring
5. **Multi-factor Auth** - Enhanced security for admin accounts

---
*Last Updated: September 1, 2025*
*Status: Production Ready with 3 Active Email Accounts*