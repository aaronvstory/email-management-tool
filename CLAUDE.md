# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Email Management Tool** is a **fully functional, production-ready** Python Flask application for local email interception, moderation, and management. It runs entirely on localhost with SQLite—no cloud services, no Docker required.

**Current Status**: ✅ **WORKING AND DEPLOYED**
**Version**: 2.2 (UI Refinements + Dark Theme Consistency)
**Last Updated**: October 1, 2025
**Recent Updates**:
- ✅ Fixed email edit button functionality with working Bootstrap modal
- ✅ Fixed search input white backgrounds (now consistent dark theme)
- ✅ Added `.input-modern` CSS class for uniform input styling
- ✅ Fixed background scrolling issue with `background-attachment: fixed`
- ✅ Darkened chart containers for theme consistency
- ✅ Comprehensive style guide created (`STYLEGUIDE.md`) - **MUST FOLLOW**
- ✅ Smart SMTP/IMAP detection implemented (auto-detects settings from email domain)
- ✅ Two permanent test accounts configured and verified (Gmail + Hostinger)
- ✅ API endpoint for auto-detection: `POST /api/detect-email-settings`
- ✅ Testing scripts created for connection validation

## Quick Start Commands

### Restarting After Port Conflicts

```bash
# Automatic cleanup and restart (recommended)
python cleanup_and_start.py

# Manual cleanup
tasklist | findstr python.exe
taskkill /F /PID <pid>
python simple_app.py
```

### Starting the Application

```bash
# Recommended: Professional launcher with menu
EmailManager.bat

# Quick start (auto-opens browser)
launch.bat

# Direct Python execution
python simple_app.py
```

**Access Points**:
- Web Dashboard: http://localhost:5000
- SMTP Proxy: localhost:8587
- Default Login: `admin` / `admin123`

## 🔑 PERMANENT TEST ACCOUNTS (DO NOT MODIFY)

**CRITICAL**: These are the ONLY two accounts with confirmed working credentials. Use these for all testing.

### Account 1: Gmail - NDayijecika (Primary Test Account)
- **Email**: ndayijecika@gmail.com
- **Password**: bjormgplhgwkgpad (Gmail App Password - no spaces in storage)
- **SMTP**: smtp.gmail.com:587 (STARTTLS, not SSL)
- **IMAP**: imap.gmail.com:993 (SSL)
- **Username**: ndayijecika@gmail.com (same as email)
- **Database ID**: 3
- **Status**: ✅ FULLY OPERATIONAL
- **Last Tested**: 2025-09-30 09:47:44
  - IMAP: ✅ Connected (9 folders found)
  - SMTP: ✅ Authenticated successfully

### Account 2: Hostinger - Corrinbox (Secondary Test Account)
- **Email**: mcintyre@corrinbox.com
- **Password**: 25Horses807$
- **SMTP**: smtp.hostinger.com:465 (SSL direct)
- **IMAP**: imap.hostinger.com:993 (SSL)
- **Username**: mcintyre@corrinbox.com (same as email)
- **Database ID**: 2
- **Status**: ✅ FULLY OPERATIONAL
- **Last Tested**: 2025-09-30 09:47:44
  - IMAP: ✅ Connected (5 folders found)
  - SMTP: ✅ Authenticated successfully

### SMTP/IMAP Smart Detection Rules

**Gmail**:
- SMTP: Port 587 with STARTTLS (smtp_use_ssl=0)
- IMAP: Port 993 with SSL
- Requires App Password (not regular password)

**Hostinger**:
- SMTP: Port 465 with SSL (smtp_use_ssl=1)
- IMAP: Port 993 with SSL

**General Rules**:
- Port 587 → Always use STARTTLS (smtp_use_ssl=0)
- Port 465 → Always use direct SSL (smtp_use_ssl=1)
- Port 993 (IMAP) → Always SSL
- Username = Email address for most providers

### Smart Detection Implementation

**Location**: `simple_app.py` lines 97-160

**Function**: `detect_email_settings(email_address: str) -> dict`
- Auto-detects SMTP/IMAP settings based on email domain
- Returns dictionary with all connection parameters
- Supports Gmail, Hostinger, Outlook, Yahoo, and generic fallback

**Supported Providers**:
| Provider | Domain | SMTP Port | IMAP Port | Notes |
|----------|--------|-----------|-----------|-------|
| Gmail | gmail.com | 587 (STARTTLS) | 993 (SSL) | Requires App Password |
| Hostinger | corrinbox.com | 465 (SSL) | 993 (SSL) | Direct SSL |
| Outlook | outlook.com, hotmail.com | 587 (STARTTLS) | 993 (SSL) | App Password for 2FA |
| Yahoo | yahoo.com | 465 (SSL) | 993 (SSL) | Direct SSL |
| Generic | any | 587 (STARTTLS) | 993 (SSL) | Fallback pattern |

### Testing Commands

```bash
# Test permanent account connections (no DB modification)
python scripts/test_permanent_accounts.py

# Setup/update permanent accounts in database
python scripts/setup_test_accounts.py

# Verify account configuration in database
python scripts/verify_accounts.py

# Quick status check (Windows batch file)
scripts\check_status.bat
```

### Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Test specific module
python -m pytest tests/test_latency_stats.py::test_name -v

# Database schema check
python -c "import sqlite3; conn = sqlite3.connect('email_manager.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(email_messages)'); print(cursor.fetchall())"

# Test email account connections
python scripts/test_all_connections.py
```

## Core Architecture

### Application Structure

**`simple_app.py`** (1700+ lines) - Monolithic Flask application containing:
- Flask web server with authentication (Flask-Login)
- SMTP proxy server (aiosmtpd on port 8587)
- IMAP monitoring threads (one per active account)
- SQLite database layer with encrypted credentials (Fernet)
- 25+ route handlers for web interface and API

**`app/routes/interception.py`** - Blueprint for interception features:
- Email hold/release/discard operations
- Email editing with diff tracking
- Attachment stripping functionality
- Stats and health endpoints

**`app/utils/`**:
- `db.py` - Database access with row_factory for dict-like results
- `crypto.py` - Fernet encryption for email credentials

### Threading Model

- **Main Thread**: Flask web server (port 5000)
- **SMTP Thread**: Email interception proxy (port 8587, daemon)
- **IMAP Threads**: Per-account monitoring (daemon, auto-reconnect)

### Email Processing Pipeline

```
1. SMTP Interception (port 8587)
   ↓
2. Risk Assessment & Storage (status=PENDING)
   ↓
3. Dashboard Review & Editing
   ↓
4. Approval/Rejection Decision
   ↓
5. SMTP Relay to Destination
   ↓
6. Audit Trail & Logging
```

### IMAP Interception Flow (Current Implementation)

```
1. IMAP IDLE on INBOX → detect new message
   ↓
2. MOVE to Quarantine folder (or COPY+DELETE fallback)
   ↓
3. Store in database (interception_status='HELD')
   ↓
4. UI Review → Edit subject/body if needed
   ↓
5. Release: APPEND back to INBOX (or discard)
```

## Database Schema

### Critical Tables

**`email_accounts`** - Encrypted IMAP/SMTP credentials per account
- Fields: `imap_host`, `imap_port`, `smtp_host`, `smtp_port`, `imap_password` (encrypted), `is_active`
- Note: `sieve_*` fields deprecated but kept for backward compatibility

**`email_messages`** - All intercepted/moderated emails with audit trail
- Key fields: `message_id`, `sender`, `recipients`, `subject`, `body_text`, `body_html`, `raw_content`
- Status: `status` (PENDING/APPROVED/REJECTED/SENT), `interception_status` (HELD/RELEASED/DISCARDED)
- Tracking: `latency_ms`, `risk_score`, `keywords_matched`, `review_notes`, `approved_by`
- Timestamps: `created_at`, `processed_at`, `action_taken_at`

**`users`** - Authentication with bcrypt password hashing
- Fields: `id`, `username`, `password_hash`, `role`, `created_at`

### Database Access Pattern

**CRITICAL**: Always use `row_factory` for dict-like access:

```python
from app.utils.db import get_db

with get_db() as conn:
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM email_messages WHERE status=?", ('PENDING',)).fetchall()
    for row in rows:
        print(row['subject'])  # Dict access, not row[2]
```

## API Endpoints

### Core Routes (simple_app.py)

```
GET  /                          # Login page
GET  /dashboard                 # Main dashboard with tabs
GET  /emails                    # Email queue (with status filter)
GET  /inbox                     # Inbox viewer
GET  /compose                   # Email composer
POST /compose                   # Send new email
GET  /accounts                  # Account management
POST /accounts/add              # Add new account (supports auto-detection)
POST /email/<id>/action         # Approve/reject email
```

### Smart Detection API

```
POST /api/detect-email-settings  # Auto-detect SMTP/IMAP settings
```

**Request**:
```json
{
  "email": "user@gmail.com"
}
```

**Response**:
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_use_ssl": false,
  "imap_host": "imap.gmail.com",
  "imap_port": 993,
  "imap_use_ssl": true
}
```

### Interception API (app/routes/interception.py)

```
GET  /api/interception/held                    # List HELD messages
GET  /api/interception/held/<id>?include_diff=1 # Detail with diff
POST /api/interception/release/<id>            # Release to inbox
POST /api/interception/discard/<id>            # Discard message
POST /api/email/<id>/edit                      # Save email edits
GET  /api/unified-stats                        # Dashboard stats (5s cache)
GET  /api/latency-stats                        # Percentile latency (10s cache)
GET  /stream/stats                             # SSE stream for live updates
GET  /healthz                                  # Health check
```

## Key Features Implementation

### Email Interception

**SMTP Proxy** (Port 8587):
```python
class EmailModerationHandler:
    async def handle_DATA(self, server, session, envelope):
        # 1. Parse email
        # 2. Calculate risk score
        # 3. Store as PENDING in database
        # 4. Return 250 Message accepted
```

**IMAP Monitoring** (Per-account threads):
- IDLE command for instant notification
- MOVE to Quarantine folder on detection
- Store raw `.eml` file for audit (raw_path)
- Record latency_ms for performance tracking

### Email Editing & Release

**Frontend**:
- **Email Viewer** (`templates/email_viewer.html`): Full-featured email display with edit capability
- **Edit Modal**: Bootstrap modal with form fields for subject/body editing
- **Working Edit Button**: Fixed implementation that properly opens modal and saves changes
- **View Modes**: Toggle between Text, HTML, and Raw email content
- **Action Buttons**: Reply, Forward, Download, Intercept/Release, Edit, Delete

**Backend**:
- `GET /email/<id>/edit` - Fetch email details for editing (returns JSON)
- `POST /api/email/<id>/edit` - Save changes to database with validation
- `POST /api/interception/release/<id>` - Rebuild MIME and APPEND to INBOX
- Diff tracking: Compare original vs edited (unified diff format)
- Attachment stripping: Optional removal with audit trail

**Critical Fix (Oct 1, 2025)**:
- Email edit button now properly fetches data and opens modal
- Added complete modal HTML structure to `email_viewer.html`
- Implemented `saveEmailEdit()` function with error handling
- Modal includes proper styling matching dark theme

### Multi-Account Management

Supports Gmail, Outlook, Hostinger, and any IMAP/SMTP provider:
- Gmail: Requires App Password (keep spaces: `xxxx xxxx xxxx xxxx`)
- Outlook: App Password for 2FA accounts
- Each account runs independent IMAP monitor thread

### Security

- **Passwords**: Encrypted with Fernet symmetric encryption (`key.txt`)
- **Sessions**: Flask-Login with secure cookies
- **Authentication**: Bcrypt password hashing for user accounts
- **Audit Trail**: All modifications logged with timestamp and user

## UI/UX Design System

**⚠️ CRITICAL**: All UI/UX work MUST follow the comprehensive style guide in `STYLEGUIDE.md`. This is mandatory for consistency and maintainability.

**Theme**: Dark-first design with red accent (#dc2626)
**Framework**: Bootstrap 5.3 with extensive custom CSS
**Icons**: Bootstrap Icons + Font Awesome 6.5

**Key Design Principles** (See `STYLEGUIDE.md` for full details):
- **Dark Theme**: Consistent dark backgrounds with proper contrast ratios
- **Fixed Background**: Body uses `background-attachment: fixed` to prevent white screen on scroll
- **Input Styling**: All inputs use `.input-modern` class with dark backgrounds
- **Chart Containers**: Dark gradients matching overall theme
- **Gradient System**: Multi-layer gradients for depth
- **Consistent Sizing**: All buttons/inputs maintain uniform height (42px standard)

**Layout**:
- Sidebar navigation (fixed left, 250px width, dark theme)
- Content area (fluid width, 20px padding, full-width)
- Cards with rounded corners (15-18px), multi-layer gradient backgrounds
- Responsive: 4 columns → 2 tablets → 1 mobile

**Color System** (from `STYLEGUIDE.md`):
```css
--primary-color: #dc2626;        /* Bright red - primary actions */
--card-bg: #1a1a1a;              /* Card background */
--text-light: #ffffff;            /* Primary text */
--grad-card: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);
```

**Component Standards**:
- All inputs: `background: rgba(255,255,255,0.06)`, white text
- Buttons: Consistent 42px height, 10px 20px padding
- Cards: Dark gradient backgrounds, 1px rgba border
- Modals: Dark backgrounds with red gradient headers

## Configuration & Settings

### Gmail Setup (For Adding New Accounts)

1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. **Use password WITH spaces**: `xxxx xxxx xxxx xxxx`
4. Enable IMAP in Gmail settings
5. SMTP: `smtp.gmail.com:587` (STARTTLS)
6. IMAP: `imap.gmail.com:993` (SSL)

## UI Development Guidelines

### Critical Requirements

**⚠️ ALWAYS consult `STYLEGUIDE.md` before making ANY UI changes!**

### Common UI Patterns

**Input Fields**:
```html
<!-- Use .input-modern class for all inputs -->
<input type="text" class="input-modern" placeholder="Enter text...">
<select class="input-modern">...</select>
<textarea class="input-modern" rows="5"></textarea>
```

**Buttons**:
```html
<!-- Standard button (42px height) -->
<button class="btn-modern btn-primary-modern">Action</button>
<button class="action-btn primary">Primary Action</button>

<!-- Small button (34px height) -->
<button class="btn-sm">Small Action</button>
```

**Cards**:
```html
<!-- Use gradient backgrounds -->
<div style="background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 18px;
            padding: 20px;">
  Card content
</div>
```

**Modals**:
```html
<!-- Dark themed modal with red gradient header -->
<div class="modal-content" style="background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);">
  <div class="modal-header" style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 50%, #7f1d1d 100%);">
    <h5 class="modal-title text-white">Title</h5>
  </div>
  <div class="modal-body" style="color: #fff;">Content</div>
</div>
```

### UI Testing Checklist

Before committing UI changes:
- [ ] Dark theme consistency maintained (no white backgrounds unless intentional)
- [ ] All inputs use `.input-modern` class or similar dark styling
- [ ] Buttons are consistent height (42px standard, 34px small, 50px large)
- [ ] Cards use gradient backgrounds, not solid colors
- [ ] Text is readable (white on dark, proper contrast)
- [ ] Hover states work and match theme
- [ ] Background doesn't show white on scroll (`background-attachment: fixed`)
- [ ] Modals use dark backgrounds with gradient headers
- [ ] Responsive design tested (desktop, tablet, mobile)

## Development Workflow

### Adding New Features

1. **Consult STYLEGUIDE.md first** if adding UI components
2. Update database schema if needed (with migration check)
3. Add route handler in `simple_app.py` or create blueprint
4. Create/update Jinja2 template in `templates/`
   - Use `.input-modern` for all inputs
   - Use gradient backgrounds for cards
   - Maintain dark theme consistency
5. Add JavaScript if interactive (inline in template)
   - Use Bootstrap 5.3 modal patterns
   - Include error handling with try-catch
   - Provide user feedback with alerts or toasts
6. Test UI checklist (see above)
7. Update this documentation

### Template Variable Injection

**Flask Context Processor** (lines 363-376 in simple_app.py):
All templates automatically receive `pending_count` for the navigation badge:

```python
@app.context_processor
def inject_pending_count():
    """Inject pending_count into all templates for the badge in navigation"""
    try:
        if current_user.is_authenticated:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            pending_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0]
            conn.close()
            return {'pending_count': pending_count}
    except:
        pass
    return {'pending_count': 0}
```

**Why This Matters**: All templates extending `base.html` need `pending_count` for the sidebar badge. The context processor automatically provides this, so individual routes don't need to pass it.

### Database Migrations

```python
# Always check for column existence first
cursor.execute('PRAGMA table_info(email_messages)')
columns = [col[1] for col in cursor.fetchall()]
if 'new_field' not in columns:
    cursor.execute('ALTER TABLE email_messages ADD COLUMN new_field TEXT')
    conn.commit()
```

### Architecture Constraints

**NO POP3 SUPPORT**: The database schema only supports IMAP/SMTP. Do not add POP3 code:
- `email_accounts` table has no `pop3_*` columns
- Only `imap_host`, `imap_port`, `smtp_host`, `smtp_port` exist
- Any POP3 references will cause SQLite column errors

## Testing Strategy

**Test Structure**:
```
tests/
├── conftest.py                    # Pytest configuration
├── test_unified_stats.py          # Dashboard stats (2 tests, all pass)
├── test_latency_stats.py          # Latency metrics (4 tests, 2 pass in suite)
└── TEST_ISOLATION_STATUS.md       # Known test limitations
```

**Known Limitation**: 2/4 latency tests fail in suite mode due to Flask singleton, but pass individually (code is correct).

**Workaround**:
```bash
python -m pytest tests/test_latency_stats.py::test_latency_stats_empty -v
```

## Troubleshooting

### Common Issues

**Gmail Authentication Failed**
→ Use App Password (with spaces), verify 2FA enabled

**Port Already in Use**
→ `netstat -an | findstr :8587` then `taskkill /F /PID <pid>`

**Database Schema Mismatch**
→ Run `python scripts/migrate_database.py`

## File Organization

```
Email-Management-Tool/
├── simple_app.py                        # Main application (THE core file)
├── email_manager.db                     # SQLite database
├── key.txt                              # Encryption key
├── requirements.txt                     # Dependencies
├── EmailManager.bat                     # Launcher
├── CLAUDE.md                            # This file - main documentation
├── PERMANENT_TEST_ACCOUNTS.md           # Permanent account guide
├── SETUP_COMPLETE.md                    # Smart detection implementation summary
├── app/
│   ├── routes/interception.py           # Interception blueprint
│   └── utils/                           # db.py, crypto.py
├── templates/                           # Jinja2 templates
├── scripts/
│   ├── test_permanent_accounts.py       # Test connections (no DB changes)
│   ├── setup_test_accounts.py           # Add/update accounts in DB
│   ├── verify_accounts.py               # Verify DB configuration
│   └── check_status.bat                 # Quick status check
├── tests/                               # Test suite
└── archive/                             # Deprecated files
```

## What Works Right Now

✅ Full email interception (SMTP + IMAP)
✅ Multi-account management with smart detection
✅ Email editing before approval with working modal UI
✅ Email viewer with Text/HTML/Raw display modes
✅ Dashboard with live stats
✅ Risk scoring and filtering
✅ Complete audit trail
✅ Attachment handling
✅ Real-time monitoring
✅ Encrypted credential storage
✅ Auto-detect SMTP/IMAP settings from email domain
✅ Two verified permanent test accounts (Gmail + Hostinger)
✅ Comprehensive testing and verification scripts
✅ Consistent dark theme with proper contrast
✅ Fixed background scrolling (no white screen)
✅ Uniform input styling with `.input-modern` class

## Important Notes

**Current Architecture**: IMAP-Only (Sieve fully deprecated)
**Technical Spec**: See `INTERCEPTION_IMPLEMENTATION.md`
**Test Status**: See `tests/TEST_ISOLATION_STATUS.md`

## Additional Documentation

For more detailed information, see:
- **STYLEGUIDE.md** - **MANDATORY** comprehensive style guide (colors, typography, components, patterns)
- **PERMANENT_TEST_ACCOUNTS.md** - Complete guide to permanent test accounts, setup commands, and troubleshooting
- **SETUP_COMPLETE.md** - Summary of smart detection implementation and test results
- **INTERCEPTION_IMPLEMENTATION.md** - Technical details of email interception architecture
- **UI_REFACTORING_COMPLETE.md** - UI/UX implementation details and design system

## Quick Reference Scripts

All scripts in `scripts/` directory:
- `test_permanent_accounts.py` - Test IMAP/SMTP connections (no DB changes)
- `setup_test_accounts.py` - Add/update accounts in database
- `verify_accounts.py` - Check database configuration
- `check_status.bat` - Quick Windows status check

---

**Remember**: This application IS working. If it's not:
1. Check `python simple_app.py` is running
2. Access http://localhost:5000
3. Verify accounts configured with `python scripts/verify_accounts.py`
4. Check `app.log` for errors
5. Test connections with `python scripts/test_permanent_accounts.py`