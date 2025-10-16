# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Email Management Tool** is a Python Flask application for local email interception, moderation, and management. Dev-focused; not production-validated. Runs entirely on localhost with SQLite—no cloud services, no Docker required.

**Current Status**: ⚠️ PARTIALLY FUNCTIONAL — requires SMTP proxy running and valid IMAP credentials stored in DB
**Version**: 2.8
**Last Updated**: October 12, 2025
**Recent Updates**:

- ✅ **Security Hardening (Phase 2+3)** - CSRF protection, rate limiting, strong SECRET_KEY generation
- ✅ **Security Validation Suite** - 4 comprehensive automated tests (100% pass rate)
- ✅ **PowerShell Setup Script** - Automated security configuration for Windows
- ✅ **Production Deployment Guide** - Complete pre-deployment checklist with validation steps
- ✅ **Workspace Cleanup** - Archived 21 redundant files (51% reduction in root clutter)
- ✅ **Post-Cleanup Verification** - All core functionality tested and working
- ✅ **Archive Organization** - Proper categorization (milestones, docs, tests, scripts)

- ✅ **Dependency-Injectable DB Layer** - db.py accepts injected connections, single-pass aggregates, WAL enforcement
- ✅ **Blueprint Modularization** - Auth, dashboard, stats, moderation, interception routes now in app/routes/*
- ✅ **Phase 1C Route Migration** - Moved accounts/emails/inbox/compose + SSE to blueprints; removed legacy duplicates
- ✅ **Monolith Reduction** - simple_app.py reduced to ~918 lines (from ~1,700+) with blueprint coverage at ~100%
- ✅ **Interception Lifecycle Tests** - Complete test suite with 100% pass rate (3/3)
- ✅ **Released Count Aggregation** - Added to `fetch_counts()` for dashboard stats
- ✅ **INTERNALDATE Extraction** - Server timestamps properly parsed and stored
- ✅ **Toast Notification System** - Replaced all browser alerts with Bootstrap 5.3 toasts
- ✅ Modern UX - Non-blocking notifications with auto-dismiss
- ✅ Dark theme toasts matching docs/STYLEGUIDE.md principles
- ✅ Confirmation prompts only for critical actions (delete)
- ✅ Fixed email edit button functionality with working Bootstrap modal
- ✅ Fixed search input white backgrounds (now consistent dark theme)
- ✅ Added `.input-modern` CSS class for uniform input styling
- ✅ Fixed background scrolling issue with `background-attachment: fixed`
- ✅ Comprehensive style guide created (`docs/STYLEGUIDE.md`) - **MUST FOLLOW**
- ✅ Smart SMTP/IMAP detection implemented (auto-detects settings from email domain)
- ✅ Two permanent test accounts configured and verified (Gmail + Hostinger)
- ✅ Phase 0 DB Hardening: Added optimized indices (status/interception/account) + WAL mode + batch fetch helpers
- ✅ Phase 1 Structural Split: Extracted IMAP workers, stats service, unified COUNT query cleanup (transitional modular layout)
- ✅ Phase 1B Route Modularization: Core routes extracted to blueprints (auth, dashboard, stats, moderation) - See "Registered Blueprints" section
- ✅ Environment Configuration: .env.example with live test toggles and credential placeholders
- ✅ NEW: Per‑account IMAP monitoring controls (start/stop) via API/UI; watchers self‑terminate on deactivate
- ✅ NEW: Live E2E interception tests (scripts/live_interception_e2e.py) using real provider SMTP/IMAP with hold→edit→release verification

## Current State Assessment (Oct 12, 2025)

**Overall**: 🟡 Partially functional — SMTP proxy must be running; IMAP watchers failing for accounts with invalid DB creds; core UI accessible.

### Key Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Monolith Size** | ~918 lines | 🟢 OK |
| **Blueprint Coverage** | 9 active blueprints | 🟢 OK |
| **Test Pass Rate** | 100% (24/24 pass) | 🟢 OK |
| **Code Coverage** | 22% overall | 🟡 Needs improvement |
| **CI/CD** | GitHub Actions configured, pytest + coverage + security audit | 🟢 OK |
| **Observability** | JSON logging + Prometheus metrics (14 types) + structured error handling | 🟢 OK |
| **Error Handling** | All 13 silent handlers fixed with contextual logging | 🟢 OK |
| **Rate Limiting** | Login (5/min), APIs (30/min): release, fetch, edit | 🟢 OK |
| **Critical Path** | Interception endpoints healthy when proxy is listening | 🟡 Requires proxy |
| **SMTP Proxy** | must be running (check /api/smtp-health) | 🟡 Depends on runtime |
| **IMAP Watchers** | Controllable per account (start/stop); require valid DB creds | 🟡 Config-dependent |
| **Security (CSRF/Rate Limit)** | Enabled and validated | 🟢 OK |

### Architecture Health

**✅ Strengths**:
- Clean blueprint separation (9 focused modules, avg 142 LOC)
- Efficient database layer (WAL mode, 6 optimized indices)
- Complete audit trail with structured logging
- Working interception lifecycle (SMTP + IMAP)

**⚠️ Known Issues**:
- **Low Test Coverage**: Only 25% code coverage (target: 50%+)
- **Helper Duplication**: 130 LOC duplicated across blueprints
- **Limited Test Suite**: 24 tests exist (need more integration & security tests)

### Top 3 Priorities (Next 2-4 Weeks)

1. ~~**Test Infrastructure Fix**~~ ✅ **COMPLETE** (Phase 0 done Oct 15, 2025)
   - ✅ Created `tests/conftest.py` with Flask fixtures
   - ✅ Added `pytest.ini` with proper test discovery
   - ✅ GitHub Actions CI configured (pytest + coverage + pip-audit)
   - **Result**: 100% pass rate (24/24 tests), 25% coverage baseline established

2. ~~**Security Hardening**~~ ✅ **COMPLETE** (Phase 2+3 done)
   - ✅ Enabled Flask-WTF CSRF protection with bidirectional validation
   - ✅ Moved SECRET_KEY to environment variable with strength validation
   - ✅ Added rate limiting to authentication endpoints (5 attempts/min)
   - ✅ Automated validation script with 4 comprehensive tests

3. ~~**Observability & Monitoring**~~ ✅ **COMPLETE** (Phase 1 done Oct 15, 2025)
   - ✅ Centralized JSON logging with RotatingFileHandler (10MB max, 5 backups)
   - ✅ Prometheus metrics endpoint at /metrics (14 metric types)
   - ✅ Comprehensive instrumentation (counters, gauges, histograms for emails, errors, latency)
   - ✅ Fixed all 13 silent error handlers (3 in interception.py, 2 in emails.py, 1 in accounts.py, 6 in simple_app.py, 1 in auth.py)
   - ✅ Added rate limiting to critical APIs: release, fetch-emails, edit (30 requests/minute)
   - ✅ Enhanced /healthz endpoint with IMAP watcher heartbeats and security status
   - ✅ 17 new tests added (5 for logging, 12 for metrics)
   - **Result**: Full observability stack operational with proper error handling and API protection, ready for production monitoring

**Detailed Analysis**: See `.claude/research/analysis/consolidated-assessment-2025-10-10.md`

## At-a-Glance

| Component            | Details                                                           |
| -------------------- | ----------------------------------------------------------------- |
| **Web Dashboard**    | http://localhost:5000 (admin / admin123)                          |
| **SMTP Proxy**       | localhost:8587                                                    |
| **Database**         | SQLite (`email_manager.db`) - local only                          |
| **Encryption**       | Fernet symmetric (`key.txt`)                                      |
| **Primary Launcher** | `EmailManager.bat` (menu) or `launch.bat` (quick)                 |
| **Test Accounts**    | Gmail (ndayijecika@gmail.com), Hostinger (mcintyre@corrinbox.com) |
| **Status Symbols**   | ✅ Working / ⚠️ Warning / ❌ Issue                                |

⚠️ **Security Note**: Permanent test accounts are for **development/testing only**. Rotate credentials if exposed. Never use in production.

## Prerequisites

- **Python**: 3.9+ (tested with 3.13)
- **Operating System**: Windows (batch scripts, path conventions)
- **Network**: Local SMTP/IMAP access (no firewall blocking ports 8587, 465, 587, 993)
- **Email Accounts**: Gmail App Passwords or provider-specific app passwords
- **Optional**: Modern browser (Chrome/Firefox/Edge) for dashboard

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
- **Password**: [REDACTED – set via .env GMAIL_PASSWORD]
- **SMTP**: smtp.gmail.com:587 (STARTTLS)
- **IMAP**: imap.gmail.com:993 (SSL)
- **Username**: ndayijecika@gmail.com (same as email)
- **Database ID**: 3
- **Status**: ✅ Live checks OK; IMAP watcher uses DB-stored password — update via Accounts if failing
- **Last Live Check**: 2025-10-12 (scripts/live_check.py)
  - IMAP: ✅ Connected
  - SMTP: ✅ Authenticated

### Account 2: Hostinger - Corrinbox (Secondary Test Account)

- **Email**: mcintyre@corrinbox.com
- **Password**: [REDACTED – set via .env HOSTINGER_PASSWORD]
- **SMTP**: smtp.hostinger.com:465 (SSL direct)
- **IMAP**: imap.hostinger.com:993 (SSL)
- **Username**: mcintyre@corrinbox.com (same as email)
- **Database ID**: 2
- **Status**: ❌ Live checks failing (IMAP/SMTP auth); verify credentials and app password
- **Last Live Check**: 2025-10-12 (scripts/live_check.py)
  - IMAP: ❌ Authentication failed
  - SMTP: ❌ Authentication failed

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

# Live end-to-end REAL provider test (hold → edit → release → verify in INBOX)
# Requires: app running, ENABLE_LIVE_EMAIL_TESTS=1, .env creds set for both accounts
python scripts/live_interception_e2e.py

# Setup/update permanent accounts in database
# Use the Accounts page (Edit) to update credentials stored in DB (watchers use DB, not .env)

# Verify account configuration in database
python scripts/verify_accounts.py

# Quick status check (Windows batch file)
scripts\check_status.bat
```

### Development Commands

### Running Tests

```bash
# Full test suite (100% pass rate - 7 tests, 20% coverage)
python -m pytest tests/ -v

# Run with coverage report
python -m pytest --cov=app --cov-report=term --cov-report=html -v

# Test specific areas
python -m pytest tests/routes/ -v                    # Route logic tests
python -m pytest tests/services/ -v                  # Service layer tests
python -m pytest tests/utils/ -v                     # Utility function tests
python -m pytest tests/live/ -v -m live              # Live email tests (requires .env)

# Test specific file
python -m pytest tests/routes/test_manual_intercept_logic.py -v

# Test single function
python -m pytest tests/routes/test_manual_intercept_logic.py::test_manual_intercept_sets_held_on_success -v

# Run with detailed output
python -m pytest tests/ -v --tb=short

# Skip live tests (default behavior)
python -m pytest tests/ -v -m "not live"
```

### Database Operations

```bash
# Check schema
python -c "import sqlite3; conn = sqlite3.connect('email_manager.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(email_messages)'); print(cursor.fetchall())"

# Verify indices (Phase 0 DB Hardening)
python scripts/verify_indices.py

# Run migrations
python scripts/migrations/20251001_add_interception_indices.py

# Test account connections
python scripts/test_permanent_accounts.py  # No DB modification
python scripts/verify_accounts.py         # Check DB config
```

### Linting & Quality

```bash
# No formal linting configured
# Code follows PEP 8 with 4-space indentation
# Flask blueprints use conventional naming
```

## Core Architecture

### Executive Summary (High-Level)

**Email Management Tool** is a Flask-based interception and moderation gateway that sits between inbound email (via SMTP proxy / IMAP monitoring) and the user's mailbox. It runs entirely on Windows (Python 3.13) with SQLite for persistence, and ships with two real test accounts (Gmail & Hostinger).

**System Layout**:
```
+---------------------+           +-----------------------+
| External senders    | --------> | SMTP Proxy (port 8587)|
+---------------------+           +-----------------------+
                                          |
                                          v
                               +-----------------------+
                               | SQLite (email_messages|
                               |  + encrypted creds)   |
                               +-----------------------+
                                          |
                                          v
                    +-----------------------------------------+
                    | Flask Dashboard (http://localhost:5000) |
                    |  Auth / Dashboard / Stats / Moderation  |
                    +-----------------------------------------+
```

**Core Capabilities**:
| Capability | How it works |
|------------|--------------|
| **Intercept inbound mail** | SMTP proxy accepts message, stores raw content, risk score, keywords, sets `status=PENDING`. IMAP watcher can also quarantine messages after delivery. |
| **Hold & release** | Dashboard lists HELD messages; admins can edit subject/body, release back to IMAP via APPEND, or discard (with audit logging). |
| **Editing** | `POST /api/email/<id>/edit` persists changes; diff shown in UI. |
| **Rules & auto-hold** | Moderation rules (UI + DB) can auto-mark messages for hold based on keywords/score. |
| **Compose/reply/forward** | Drafts through the web UI hit SMTP providers directly (STARTTLS or SSL depending on port). |
| **Audit trail** | audit.py logs actions (LOGIN, INTERCEPT, RELEASE, etc.) for traceability. |
| **Live stats** | stats.py caches aggregated counts (total, pending, held, released, etc.) with TTL; SSE endpoint streams updates. |

### Application Structure

**`simple_app.py`** (~918 lines) - Core application bootstrap and services; all web routes live in blueprints:

- Flask web server with authentication (Flask-Login)
- SMTP proxy server (aiosmtpd on port 8587)
- IMAP monitoring threads (one per active account)
- SQLite database layer with encrypted credentials (Fernet)
- 25+ route handlers for web interface and API (Legacy routes - being migrated to blueprints)

### Registered Blueprints (Phase 1B/1C Modularization)

**`app/routes/auth.py`** - Authentication blueprint:
- Routes: `/`, `/login`, `/logout`
- Uses: `app.models.simple_user.SimpleUser`, `app.services.audit.log_action`

**`app/routes/dashboard.py`** - Dashboard blueprint:
- Routes: `/dashboard`, `/dashboard/<tab>`, `/test-dashboard`
- Features: Account selector, stats display, recent emails, rules overview

**`app/routes/stats.py`** - Statistics API blueprint:
- Routes: `/api/stats`, `/api/unified-stats`, `/api/latency-stats`, `/stream/stats`, `/api/events` (SSE)
- Features: 2s-5s caching, SSE streaming for real-time updates

**`app/routes/moderation.py`** - Moderation blueprint:
- Routes: `/rules`
- Features: Admin-only access, rule management interface

**`app/routes/interception.py`** - Interception blueprint (Phase 1A):
- Email hold/release/discard operations
- Email editing with diff tracking
- Attachment stripping functionality
- Health and diagnostic endpoints

**`app/routes/emails.py`** - Emails blueprint (Phase 1C):
- Routes: `/emails`, `/email/<id>`, `/email/<id>/action`, `/email/<id>/full`, `/api/fetch-emails`, `/api/email/<id>/reply-forward`, `/api/email/<id>/download`
- Features: Queue, viewer, reply/forward helpers, .eml download, IMAP UID fetch

**`app/routes/accounts.py`** - Accounts blueprint (Phase 1C):
- Routes: `/accounts`, `/accounts/add`, `/api/accounts`, `/api/accounts/<id>` (GET/PUT/DELETE), `/api/accounts/<id>/health`, `/api/accounts/<id>/test`, `/api/accounts/export`, `/api/test-connection/<type>`, `/api/accounts/<id>/monitor/start`, `/api/accounts/<id>/monitor/stop`, `/diagnostics[/<id>]`
- Features: Smart detection API, connectivity tests, export, diagnostics redirect, per‑account IMAP watcher control (start/stop)

**`app/routes/inbox.py`** - Inbox blueprint (Phase 1C):
- Route: `/inbox`
- Features: Unified inbox view by account

**`app/routes/compose.py`** - Compose blueprint (Phase 1C):
- Routes: `/compose` (GET, POST)
- Features: Email composition and sending via SMTP
- Supports both form and JSON API requests
- SMTP connection with SSL/STARTTLS support

**`app/models/simple_user.py`** - Lightweight User model:
- SimpleUser class for Flask-Login integration
- Replaces inline User class in simple_app.py
- Independent of SQLAlchemy models

**`app/services/audit.py`** - Audit logging service:
- log_action() - Best-effort audit logging
- get_recent_logs() - Retrieve audit history
- SQLite-based with silent failure pattern

**`app/utils/`**:
- `db.py` - Dependency-injectable database layer with row_factory for dict-like results
  - `get_db(db_path=None, conn=None)` - Returns context manager for DB access
  - `fetch_counts(conn=None)` - Single-pass aggregate query for all dashboard stats
  - Enforces WAL mode, foreign keys, busy_timeout
- `crypto.py` - Fernet encryption for email credentials

### Threading Model

- **Main Thread**: Flask web server (port 5000)
- **SMTP Thread**: Email interception proxy (port 8587, daemon)
- **IMAP Threads**: Per-account monitoring (daemon, auto-reconnect)
  - Controlled by `ENABLE_WATCHERS` env var (default: enabled)
  - Started via `app/workers/imap_startup.py::start_imap_watchers()`
  - All threads share SQLite DB; WAL + busy_timeout mitigate contention

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

### Performance Indices (Phase 0 DB Hardening)

**Optimized indices added for fast filtering and aggregation:**

- `idx_email_messages_interception_status` - Filter by HELD/RELEASED/DISCARDED
- `idx_email_messages_status` - Filter by PENDING/APPROVED/REJECTED/SENT
- `idx_email_messages_account_status` - Per-account status filtering
- `idx_email_messages_account_interception` - Per-account interception filtering
- `idx_email_messages_direction_status` - Direction + interception queries
- `idx_email_messages_original_uid` - IMAP UID lookups

**Query optimizer benefits:**
- Dashboard COUNT queries use covering indices (no table scan)
- Account-specific queries leverage composite indices
- WAL mode enabled for concurrent read/write performance

**Migration:** Run `python scripts/migrations/20251001_add_interception_indices.py`
**Verification:** Run `python scripts/verify_indices.py` to see query plans

### Transitional Layout (Phase 1 Structural Split)

**Modular components extracted from simple_app.py monolith:**

- **app/services/stats.py**: Unified statistics with 2-second TTL caching
  - `get_stats()` - Dashboard stats with automatic cache
  - `clear_cache()` - Force cache invalidation
  - `get_cache_info()` - Cache metadata for monitoring

- **app/workers/imap_startup.py**: IMAP watcher initialization
  - `start_imap_watchers()` - Start threads for active accounts
  - `ENABLE_WATCHERS` environment variable for control

- **Unified COUNT query cleanup**: 2 more endpoints refactored in simple_app.py
  - `api_unified_stats` (line 2217)
  - `unified_counts` helper (line 2287)
  - Total Phase 0+1: 7 endpoints using `fetch_counts()`

**Testing**: Run `python -m pytest tests/test_stats.py -v` for cache validation

**Next Phase**: Full blueprint migration (routes → app/routes/*, complete modularization)

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
- Extracts INTERNALDATE (server timestamp) and original_uid from IMAP

**Interception Specifics**:
1. **SMTP path**:
   - `EmailModerationHandler.handle_DATA` stores message, populates risk metadata, returns 250
   - Optionally triggers rule-based auto-holds
2. **IMAP path**:
   - Threads select INBOX, IDLE, fetch new UIDs, move to Quarantine
   - Database row updated to `interception_status='HELD'`, `original_uid` captured
3. **Release**:
   - `app/routes/interception.py::release_email` rebuilds MIME (optionally using edited body)
   - APPENDs to INBOX, sets `interception_status='RELEASED'` + `status='DELIVERED'`
4. **Manual intercept** (already inboxed):
   - `POST /api/email/<id>/intercept` can re-open and programmatically move messages from inbox back into hold
   - Computes latency and logs the action

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

**⚠️ CRITICAL**: All UI/UX work MUST follow the comprehensive style guide in `docs/STYLEGUIDE.md`. This is mandatory for consistency and maintainability.

**Theme**: Dark-first design with red accent (#dc2626)
**Framework**: Bootstrap 5.3 with extensive custom CSS
**Icons**: Bootstrap Icons + Font Awesome 6.5

**Key Design Principles** (See `docs/STYLEGUIDE.md` for full details):

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

**Color System** (from `docs/STYLEGUIDE.md`):

```css
--primary-color: #dc2626; /* Bright red - primary actions */
--card-bg: #1a1a1a; /* Card background */
--text-light: #ffffff; /* Primary text */
--grad-card: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);
```

**Component Standards**:

- All inputs: `background: rgba(255,255,255,0.06)`, white text
- Buttons: Consistent 42px height, 10px 20px padding
- Cards: Dark gradient backgrounds, 1px rgba border
- Modals: Dark backgrounds with red gradient headers

## Configuration & Settings

### Environment Variables

**`.env` file** (not committed) - Optional configuration overrides:
- `DB_PATH` - Override default SQLite database path
- `ENABLE_WATCHERS` - Enable/disable IMAP monitoring threads (default: 1)
- `ENABLE_LIVE_EMAIL_TESTS` - Gate live email tests (default: 0)
- `LIVE_EMAIL_ACCOUNT` - Which test account to use (gmail or hostinger)
- `GMAIL_ADDRESS`, `GMAIL_PASSWORD` - Gmail test credentials
- `HOSTINGER_ADDRESS`, `HOSTINGER_PASSWORD` - Hostinger test credentials

**`.env.example`** - Template with all configuration options and credential placeholders

### Gmail Setup (For Adding New Accounts)

1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. **Use password WITH spaces**: `xxxx xxxx xxxx xxxx`
4. Enable IMAP in Gmail settings
5. SMTP: `smtp.gmail.com:587` (STARTTLS)
6. IMAP: `imap.gmail.com:993` (SSL)

## Security Hardening & Validation

**Status**: ✅ **PRODUCTION-READY SECURITY** (as of Phase 2+3 completion)

The Email Management Tool includes comprehensive security hardening with CSRF protection, rate limiting, and strong SECRET_KEY generation. All security features are validated through automated tests.

### Security Features

| Feature | Implementation | Status |
|---------|----------------|--------|
| **CSRF Protection** | Flask-WTF with bidirectional validation | ✅ Enabled |
| **Rate Limiting** | Flask-Limiter on authentication endpoints | ✅ Enabled (5 attempts) |
| **Strong SECRET_KEY** | 64-char hex token via cryptographic RNG | ✅ Validated |
| **Session Security** | Flask-Login with secure cookies | ✅ Enabled |
| **Credential Encryption** | Fernet symmetric encryption | ✅ Enabled |
| **Audit Logging** | All security events logged | ✅ Enabled |

### Initial Security Setup (Windows)

**Option 1: PowerShell Setup (Recommended)**

```powershell
# Run from project root
.\setup_security.ps1
```

**What it does**:
- Creates `.env` from `.env.example` if missing
- Generates strong 64-character hex SECRET_KEY using cryptographic RNG
- Detects weak/placeholder secrets and regenerates automatically
- Compatible with PowerShell 5.1+ and PowerShell Core

**Weak Secret Detection**:
The script automatically detects and replaces these placeholder values:
- `dev-secret-change-in-production`
- `change-this-to-a-random-secret-key`
- `your-secret-here`
- Any secret shorter than 32 characters

**Option 2: Bash Setup (Git Bash/WSL)**

```bash
# Run from project root
./setup_security.sh
```

### Security Validation

After setup, validate all security features are working:

```bash
# Run validation script (preferred method)
python -m scripts.validate_security

# Alternative: Run from scripts directory
cd scripts && python validate_security.py
```

**What it validates** (4 comprehensive tests):

1. **SECRET_KEY Strength** - Verifies:
   - Length ≥ 32 characters
   - Entropy ≥ 4.0 bits/char (or 64+ hex chars)
   - Not in weak secret blacklist
   - **Does not expose secret value**

2. **CSRF Negative Test** - Blocks login without token:
   - Submits valid credentials WITHOUT csrf_token
   - Expects 400 status or redirect back to /login
   - Ensures dashboard is not accessible

3. **CSRF Positive Test** - Allows login with valid token:
   - Extracts CSRF token from /login page
   - Submits credentials WITH valid token
   - Expects redirect to /dashboard

4. **Rate Limiting** - Triggers 429 after threshold:
   - Sends 6 failed login attempts with valid CSRF
   - Uses JSON requests to force 429 response
   - Checks for rate limit headers (Retry-After, X-RateLimit-Remaining)

**Expected Output (All Passing)**:

```
Test 0 (SECRET_KEY strength: len>=32, entropy>=4.0, not blacklisted): PASS  [len=64, blacklisted=False, entropy=4.00 bits/char]
Test 1 (missing CSRF blocks login): PASS  [status=400, location='']
Test 2 (valid CSRF allows login): PASS  [status=302, location='/dashboard']
Test 3 (rate limit triggers 429/headers): PASS  [codes=[401, 401, 401, 401, 401, 429], headers_subset={'Retry-After': '60', 'X-RateLimit-Remaining': '0'}]

Summary:
  SECRET_KEY: OK (len=64, entropy=4.00 bpc)
  CSRF missing-token block: OK
  CSRF valid-token success: OK
  Rate limit: OK
```

### Security Configuration Details

**CSRF Configuration** (`simple_app.py`):
- **Token Expiry**: None (tokens valid for session lifetime)
- **Cookie Settings**: SameSite=Lax, Secure in production
- **Exempt Routes**: SSE streams (`/stream/stats`, `/api/events`)
- **Error Handling**: User-friendly 400 handler with instructions
- **AJAX Support**: Automatic CSRF header injection via `static/js/app.js`

**Rate Limiting Configuration**:
- **Login Endpoint**: 5 attempts per minute per IP
- **Storage**: In-memory (single instance) or Redis (distributed)
- **Error Handling**: User-friendly 429 handler with retry guidance
- **JSON Support**: Returns 429 with Retry-After header

**SECRET_KEY Management**:
- **Source**: Environment variable `FLASK_SECRET_KEY` from `.env`
- **Generation**: PowerShell uses `[System.Security.Cryptography.RandomNumberGenerator]`
- **Fallback**: Hardcoded dev secret (triggers validation warning)
- **Rotation**: Change `FLASK_SECRET_KEY` in `.env` and restart app

### Troubleshooting Security Issues

**Validation Fails on SECRET_KEY**:
```bash
# Regenerate SECRET_KEY
.\setup_security.ps1  # Will detect weak secret and regenerate
```

**CSRF Token Missing in Forms**:
- Check template includes `<meta name="csrf-token" content="{{ csrf_token() }}">`
- For forms: Include `{{ form.hidden_tag() }}` or `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
- For AJAX: Use `X-CSRFToken` header (auto-injected by `static/js/app.js`)

**Rate Limit Not Working**:
- Verify Flask-Limiter installed: `pip install Flask-Limiter`
- Check logs for rate limit warnings
- Test with JSON requests to force 429 response

**CSRF Errors in Development**:
```bash
# Disable SSL requirement for CSRF cookies (dev only)
# In simple_app.py:
app.config['WTF_CSRF_SSL_STRICT'] = False  # Already set for localhost
```

### Security Health Endpoint

Check security configuration status (without exposing secrets):

```bash
# Query health endpoint
curl http://localhost:5000/healthz
```

**Enhanced Response (v2.7+)**:
```json
{
  "ok": true,
  "db": "ok",
  "held_count": 0,
  "released_24h": 0,
  "median_latency_ms": null,
  "workers": [],
  "timestamp": "2025-10-10T12:00:00Z",
  "security": {
    "secret_key_configured": true,
    "secret_key_prefix": "a1b2c3d4",
    "csrf_enabled": true,
    "csrf_time_limit": null,
    "session_cookie_secure": false,
    "session_cookie_httponly": true
  }
}
```

**Response Fields**:
- `ok` - Overall health status (true/false)
- `db` - Database connectivity ("ok" or null if error)
- `held_count` - Number of currently held messages
- `released_24h` - Messages released in last 24 hours
- `median_latency_ms` - Median interception latency (milliseconds)
- `workers` - IMAP worker heartbeat status
- `timestamp` - ISO 8601 UTC timestamp
- `security` - Security configuration status (NEW in v2.7):
  - `secret_key_configured` - Is SECRET_KEY strong (≥32 chars)?
  - `secret_key_prefix` - First 8 chars of SECRET_KEY for verification (not full secret)
  - `csrf_enabled` - CSRF protection status
  - `csrf_time_limit` - Token expiry (null = no expiry)
  - `session_cookie_secure` - Secure flag status
  - `session_cookie_httponly` - HttpOnly flag status

**Security Note**: Only the first 8 characters of SECRET_KEY are exposed for verification purposes. Full secret is never transmitted.

## UI Development Guidelines

### Critical Requirements

**⚠️ ALWAYS consult `docs/STYLEGUIDE.md` before making ANY UI changes!**

### Common UI Patterns

**Input Fields**:

```html
<!-- Use .input-modern class for all inputs -->
<input type="text" class="input-modern" placeholder="Enter text..." />
<select class="input-modern">
  ...
</select>
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
<div
  style="background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 18px;
            padding: 20px;"
>
  Card content
</div>
```

**Toast Notifications** (NEW - v2.3):

```javascript
// Success notification (green)
showSuccess("Operation completed successfully");

// Error notification (red)
showError("Failed to process request");

// Warning notification (orange)
showWarning("Please select an account first");

// Info notification (blue)
showInfo("Processing your request...");

// Confirmation for critical actions (orange with Cancel/Confirm)
confirmToast(
  "Permanently discard this email?",
  () => {
    // User confirmed - execute action
    deleteEmail(id);
  },
  () => {
    // User cancelled (optional callback)
  }
);
```

**Toast Features**:

- Auto-dismiss after 4-5 seconds (configurable)
- Manual close button always available
- Top-right positioning with slide-in animation
- Dark theme matching docs/STYLEGUIDE.md
- Non-blocking user experience
- Only use `confirmToast()` for destructive actions (delete, discard)

**Modals**:

```html
<!-- Dark themed modal with red gradient header -->
<div
  class="modal-content"
  style="background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);"
>
  <div
    class="modal-header"
    style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 50%, #7f1d1d 100%);"
  >
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
- [ ] **Toast notifications used** (not browser alerts) for all user feedback
- [ ] Responsive design tested (desktop, tablet, mobile)

## Development Workflow

### Adding New Features

1. **Consult docs/STYLEGUIDE.md first** if adding UI components
2. Update database schema if needed (with migration check)
3. Add route handler in `simple_app.py` or create blueprint
4. Create/update Jinja2 template in `templates/`
   - Use `.input-modern` for all inputs
   - Use gradient backgrounds for cards
   - Maintain dark theme consistency
5. Add JavaScript if interactive (inline in template)
   - Use Bootstrap 5.3 modal patterns
   - Include error handling with try-catch
   - **Use toast notifications** (see Toast Notifications section above for details)
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
├── test_intercept_flow.py         # Interception lifecycle (3 tests, all pass) ✅ NEW
└── TEST_ISOLATION_STATUS.md       # Known test limitations
```

**Test Coverage**:
- ✅ **Interception Lifecycle** (test_intercept_flow.py) - 100% pass rate (3/3)
  - `test_fetch_stores_uid_and_internaldate` - Verifies IMAP fetch stores UID and server timestamp
  - `test_manual_intercept_moves_and_latency` - Validates HELD status with remote MOVE and latency calculation
  - `test_release_sets_delivered` - Confirms RELEASED/DELIVERED transition after email edit
- ✅ **Dashboard Stats** (test_unified_stats.py) - 100% pass rate (2/2)
- ⚠️ **Latency Metrics** (test_latency_stats.py) - 50% pass rate (2/4 in suite, all pass individually)

**Running Tests**:

```bash
# Run all interception tests (recommended)
python -m pytest tests/test_intercept_flow.py -v

# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_intercept_flow.py::test_fetch_stores_uid_and_internaldate -v
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
├── key.txt                              # Encryption key (CRITICAL - do not delete)
├── requirements.txt                     # Dependencies
├── EmailManager.bat                     # Primary launcher (menu-driven)
├── launch.bat                           # Quick start launcher
├── CLAUDE.md                            # This file - main documentation
├── app/
│   ├── routes/interception.py           # Interception blueprint
│   └── utils/                           # db.py, crypto.py
├── docs/                                # Documentation
│   ├── STYLEGUIDE.md                    # UI/UX standards (MUST FOLLOW)
│   ├── INTERCEPTION_IMPLEMENTATION.md   # Technical architecture details
│   ├── architecture/                    # Architecture diagrams
│   ├── reports/                         # Analysis reports
│   └── setup/                           # Setup guides
├── static/
│   ├── js/app.js                        # Toast notification system (v2.3)
│   └── css/theme-dark.css               # Dark theme styling
├── templates/                           # Jinja2 templates
├── scripts/
│   ├── test_permanent_accounts.py       # Test connections (no DB changes)
│   ├── setup_test_accounts.py           # Add/update accounts in DB
│   ├── verify_accounts.py               # Verify DB configuration
│   └── check_status.bat                 # Quick status check
├── tests/                               # Test suite (pytest)
├── archive/                             # Historical files (see archive/README.md)
│   ├── docs/                            # Superseded documentation
│   ├── scripts/                         # Old utility scripts
│   ├── milestones/                      # Completion markers from past phases
│   ├── backups/                         # Backup files from major refactors
│   ├── old-templates/                   # Legacy HTML templates
│   ├── system_dumps/                    # Diagnostic crash dumps
│   ├── databases/                       # Deprecated database files
│   ├── launchers/                       # Lesser-used batch files
│   └── test-reports/                    # Historical test artifacts
├── screenshots/                         # UI screenshots
│   └── archive/                         # Outdated screenshots
└── initial/                             # Original codebase snapshot
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
✅ **Modern toast notification system** (v2.3) - No more browser alerts!
✅ **Production-ready security** (Phase 2+3):
  - CSRF protection with bidirectional validation
  - Rate limiting (5 attempts/min on login)
  - Strong SECRET_KEY generation (64-char hex)
  - Automated security validation (4 tests, 100% pass)
  - PowerShell setup script for Windows

## Deployment & Production Considerations

### Running in Production

**Prerequisites**:
- Python 3.9+ (tested with 3.13)
- Windows environment (batch scripts assume Windows)
- Network access to IMAP/SMTP servers (ports 465, 587, 993)
- Email accounts with App Passwords configured

**Deployment Checklist**:
1. ✅ Clone repository to `C:\claude\Email-Management-Tool`
2. ✅ Install dependencies: `pip install -r requirements.txt`
3. ✅ Generate encryption key (automatic on first run, saves to `key.txt`)
4. ✅ **Run security setup**: `.\setup_security.ps1` (generates strong SECRET_KEY)
5. ✅ **Validate security**: `python -m scripts.validate_security` (all 4 tests must pass)
6. ✅ Configure accounts via web dashboard or `scripts/setup_test_accounts.py`
7. ✅ Optionally create `.env` file with overrides
8. ✅ Run database migrations if upgrading: `python scripts/migrations/*.py`
9. ✅ Verify indices: `python scripts/verify_indices.py`
10. ✅ Start application: `EmailManager.bat` or `python simple_app.py`

**Security Notes**:
- `key.txt` is CRITICAL - backup securely, never commit to version control
- `.env` contains credentials - add to `.gitignore`, never commit
- Default admin account (`admin`/`admin123`) should be changed in production
- SMTP proxy (port 8587) should only be accessible locally

### Pre-Deployment Security Verification

**CRITICAL**: Complete this checklist before deploying to production or exposing to network access.

#### Step 1: Initial Security Setup

```powershell
# Run from project root (Windows PowerShell)
.\setup_security.ps1
```

**Expected Output**:
```
🔐 Email Management Tool - Security Setup (PowerShell)
✓ .env file exists
✓ SECRET_KEY already configured (looks strong)

✅ Security setup complete!

Next steps:
  1) Review .env and adjust values if needed
  2) Start app: python simple_app.py
  3) Run validation: .\validate_security.sh (Git Bash) or python -m scripts.validate_security
```

**If weak secret detected**:
```
Weak or placeholder FLASK_SECRET_KEY detected – regenerating...
✓ SECRET_KEY generated
```

#### Step 2: Validate Security Configuration

```bash
# From project root
python -m scripts.validate_security
```

**Required Result**: All 4 tests must pass

| Test | What It Checks | Pass Criteria |
|------|----------------|---------------|
| **Test 0** | SECRET_KEY strength | len≥32, entropy≥4.0, not blacklisted |
| **Test 1** | CSRF blocks invalid requests | Returns 400 or redirects to /login |
| **Test 2** | CSRF allows valid requests | Redirects to /dashboard with token |
| **Test 3** | Rate limiting active | 429 status after 5 attempts |

**Failure Actions**:

| Failed Test | Fix |
|-------------|-----|
| **Test 0 (SECRET_KEY)** | Run `.\setup_security.ps1` again |
| **Test 1 (CSRF block)** | Check Flask-WTF installed: `pip install Flask-WTF` |
| **Test 2 (CSRF allow)** | Verify CSRF meta tag in login template |
| **Test 3 (Rate limit)** | Check Flask-Limiter: `pip install Flask-Limiter` |

#### Step 3: Verify Environment Configuration

```bash
# Check .env file exists and has required values
cat .env | grep FLASK_SECRET_KEY
```

**Required Variables**:
- `FLASK_SECRET_KEY` - Must be 64-char hex (not placeholder)
- `DB_PATH` - Optional, defaults to `email_manager.db`
- `ENABLE_WATCHERS` - Optional, defaults to 1

**Security Red Flags** (Never use these values):
```
FLASK_SECRET_KEY=dev-secret-change-in-production  ❌ WEAK
FLASK_SECRET_KEY=change-this-to-a-random-secret-key  ❌ WEAK
FLASK_SECRET_KEY=your-secret-here  ❌ WEAK
FLASK_SECRET_KEY=secret  ❌ WEAK
```

#### Step 4: Test Application Security

```bash
# Start application
python simple_app.py

# In another terminal, check health endpoint
curl http://localhost:5000/healthz
```

**Expected Health Response**:
```json
{
  "ok": true,
  "db": "ok",
  "held_count": 0,
  "released_24h": 0,
  "median_latency_ms": null,
  "workers": [],
  "timestamp": "2025-10-10T12:00:00Z"
}
```

**Manual Security Tests**:
1. **CSRF Protection**:
   - Try logging in without opening /login first → Should fail
   - Open /login, inspect page source → Should see `<meta name="csrf-token">`

2. **Rate Limiting**:
   - Try 6 failed logins rapidly → Should see rate limit error after 5th attempt
   - Wait 60 seconds → Should be able to try again

3. **Session Security**:
   - Log in successfully → Should redirect to /dashboard
   - Close browser, reopen → Should still be logged in (session cookie)
   - Check browser cookies → Should see `session` cookie with HttpOnly flag

#### Step 5: Production Configuration Review

**Before Production Deployment**:

```bash
# Change default admin password
# 1. Log in to dashboard as admin/admin123
# 2. Navigate to user management (if available) or update database directly:
sqlite3 email_manager.db
sqlite> UPDATE users SET password_hash = '<new_bcrypt_hash>' WHERE username = 'admin';
```

**Environment Variable Checklist**:
- [ ] `FLASK_SECRET_KEY` is strong (64 chars, high entropy)
- [ ] `.env` is in `.gitignore` and never committed
- [ ] `key.txt` (Fernet encryption key) is backed up securely
- [ ] SMTP proxy port 8587 is firewalled (localhost only)
- [ ] Flask port 5000 is behind reverse proxy (nginx/Apache) if exposed
- [ ] HTTPS enabled if accessible over network (not just localhost)
- [ ] Default admin password changed from `admin123`

#### Step 6: Post-Deployment Verification

After deployment, verify all security features:

```bash
# Run validation against deployed instance
python -m scripts.validate_security

# Check logs for security events
tail -f app.log | grep -i "security\|csrf\|rate"

# Monitor health endpoint
watch -n 30 curl http://localhost:5000/healthz
```

**Common Deployment Issues**:

| Issue | Symptom | Fix |
|-------|---------|-----|
| **CSRF token errors** | "The CSRF token is missing" | Add `<meta name="csrf-token">` to templates |
| **Rate limit not working** | No 429 errors after spam | Install Flask-Limiter, restart app |
| **Session expires immediately** | Logged out on refresh | Check SECRET_KEY is stable (not regenerating) |
| **HTTPS CSRF errors** | CSRF fails on HTTPS only | Set `WTF_CSRF_SSL_STRICT = True` for HTTPS |

### Security Monitoring & Maintenance

**Daily Checks**:
- Monitor `app.log` for CSRF violations and rate limit triggers
- Check `/healthz` endpoint for database connectivity
- Verify IMAP worker heartbeats are active

**Weekly Checks**:
- Review audit_log table for suspicious activity
- Check for failed login patterns (brute force attempts)
- Verify backup integrity (`.env`, `key.txt`, `email_manager.db`)

**Monthly Tasks**:
- Consider rotating `FLASK_SECRET_KEY` (invalidates all sessions)
- Review and update dependencies: `pip list --outdated`
- Test disaster recovery (restore from backups)

**Monitoring & Logs**:
- Application log: `app.log` (Flask + SMTP/IMAP events)
- Audit trail: `audit_log` table in database
- Live stats: SSE stream at `/stream/stats`
- Health check: `GET /healthz`

### Configuration Toggles

**Environment Variables** (via `.env`):
```bash
# Database
DB_PATH=email_manager.db

# IMAP monitoring
ENABLE_WATCHERS=1  # 0 to disable IMAP threads (dev mode)

# Testing
ENABLE_LIVE_EMAIL_TESTS=0  # 1 to enable live tests
LIVE_EMAIL_ACCOUNT=gmail   # or 'hostinger'

# Credentials (for testing only - values MUST be set locally in .env)
GMAIL_ADDRESS=ndayijecika@gmail.com
GMAIL_PASSWORD=
HOSTINGER_ADDRESS=mcintyre@corrinbox.com
HOSTINGER_PASSWORD=
```

## Important Notes

**Current Architecture**: IMAP-Only (Sieve fully deprecated)
**Technical Spec**: See `INTERCEPTION_IMPLEMENTATION.md`
**Test Status**: See `tests/TEST_ISOLATION_STATUS.md`
**Environment Config**: See `.env.example` for all configuration options

## Test Status & Known Issues

### Current Test Suite Status (as of 2025-10-15)

**Overall**: ✅ **100% pass rate (7/7 tests), 20% code coverage**
**Infrastructure**: ✅ Test discovery fixed, pytest configured, CI/CD pipeline ready

| Test Category | Tests | Pass Rate | Coverage | Status |
|--------------|-------|-----------|----------|--------|
| **Interception Lifecycle** | 1 test (live e2e) | 100% | - | ✅ Core flow working |
| **Manual Intercept Logic** | 2 tests | 100% | - | ✅ HOLD/MOVE operations validated |
| **IMAP Watcher Decisions** | 2 tests | 100% | - | ✅ Rule engine integration working |
| **Rule Engine Schemas** | 2 tests | 100% | 69% | ✅ Multiple schema support validated |
| **Overall Coverage** | 7 tests | 100% | 20% | 🟡 Needs expansion |

### Infrastructure Improvements (Phase 0 - Oct 15, 2025)

**✅ Completed**:
1. **tests/conftest.py** - Comprehensive Flask app, client, and DB fixtures
2. **pytest.ini** - Proper test discovery, excludes archive/, custom markers
3. **GitHub Actions CI** - Automated testing with coverage reports and pip-audit
4. **Test Reality Check** - Documented actual test count (7, not 96.7% of 110)

### Test Coverage Gaps

**Critical Paths Undertested** (sorted by priority):
1. **IMAP Watcher** (19% coverage) - Thread lifecycle, reconnection, IDLE loop
2. **Email Routes** (19% coverage) - Fetch, viewer, reply/forward operations
3. **Accounts Management** (14% coverage) - CRUD operations, health checks
4. **Interception Routes** (24% coverage) - Release, discard, edit operations
5. **Security Features** (0% coverage) - CSRF bypass attempts, rate limit validation

### Recommended Next Steps

**Phase 1: Expand Core Test Suite** (2-4 hours):
- Add integration tests for SMTP proxy + IMAP watcher interaction
- Add security tests for CSRF protection and rate limiting
- Add database transaction rollback tests
- **Target**: 40% coverage, 20+ tests

**Phase 2: CI/CD Hardening** (1-2 hours):
- Add pre-commit hooks (black, isort, flake8)
- Configure coverage threshold enforcement (fail CI below 30%)
- Add test result badges to README

**Phase 3: Performance Testing** (2-3 hours):
- Load testing for interception pipeline (emails/sec throughput)
- Latency percentiles under concurrent load
- Memory leak detection for long-running IMAP watchers

### Current Status & Gaps (as of Oct 2, 2025)

**Completed**:
- ✅ Dependency-injectable DB layer (db.py now accepts injected connections)
- ✅ Single-pass aggregates (fetch_counts using efficient queries)
- ✅ WAL mode + foreign keys enforced
- ✅ Blueprint modularization (auth, dashboard, stats, moderation, interception)
- ✅ Centralized logging/audit helpers
- ✅ Three new pytest cases for interception lifecycle
- ✅ UI modernization (toast notifications, dark theme fixes, working edit modal)
- ✅ DB hardening (targeted indices + verification script)
- ✅ Two vetted live test accounts documented

**Outstanding Tasks**:
| Area | What's missing | Suggested next move |
|------|----------------|---------------------|
| **Test harness** | 62/110 pytest cases fail due to missing fixtures/import changes after Phase 1B | Build new conftest.py (Flask app/client fixtures, DB session), add compatibility module for old imports, update pytest markers |
| **Blueprint migration** | Email CRUD, accounts, diagnostics routes still in simple_app.py | Continue Phase 1C: move email/account/compose endpoints into routes |
| **Integration testing** | No automated live IMAP/SMTP run | Optional: create gated pytest integration suite using real accounts + dotenv toggles |
| **CI pipeline** | No lint/test pipeline | Plan for GitHub Actions/pytest job after suite is stable |
| **Docs** | Need high-level diagrams & quick-start for engineers | Executive summary now added to CLAUDE.md; expand diagrams later |

**Recommended Immediate Focus**:
1. Finish Phase 1C blueprint split (email CRUD + account routes)
2. Test infrastructure: new conftest.py, dependency-injected DB for counts/stats tests, import adapters
3. Optional live integration suite: gated by .env to exercise Gmail/Hostinger end-to-end
4. CI pipeline: once tests stable, add PyTest job to GitHub Actions

### Recommended Testing Strategy

**For Development**:
```bash
# Use working test suites
python -m pytest tests/interception/ -v
python -m pytest tests/test_complete_application.py::TestEmailDiagnostics -v
```

**For CI/CD** (when implemented):
```bash
# Exclude broken imports until Phase 1 fixes complete
python -m pytest tests/ --ignore=tests/integration --ignore=tests/unit/frontend
```

## Deep Dive Addendum (v2.8) — Architecture, State Machines, and Troubleshooting Playbooks

This addendum expands on the practical internals, state transitions, failure modes, and provider nuances of the Email Management Tool. It complements docs/INTERCEPTION_IMPLEMENTATION.md and serves as an operational guide for engineers.

### 1) End-to-End Dataflows (Detailed)

- SMTP Interception Path (port 8587):
  1. aiosmtpd accepts DATA → parse MIME → normalize headers
  2. Risk evaluation (keywords + rule engine) → initial risk_score
  3. Persist to SQLite (email_messages: raw_content, body_text/html, status=PENDING, interception_status=HELD when auto-hold)
  4. Emit audit log (INTERCEPT) and stats cache invalidation
  5. UI lists HELD/PENDING; actions via POST endpoints

- IMAP Watch Path (per active account):
  1. Connect (SSL 993 or STARTTLS 143) → select INBOX → IDLE loop with backoff
  2. On new UID: FETCH INTERNALDATE, FLAGS, ENVELOPE; capture server timestamp
  3. MOVE to Quarantine (or COPY+DELETE when MOVE unsupported) → record HELD
  4. Persist/update row: original_uid, interception_status=HELD, latency_ms computed if applicable

- Release Path:
  1. Rebuild MIME (edited subject/body respected)
  2. APPEND → INBOX on provider → set interception_status=RELEASED, status=DELIVERED
  3. Audit (RELEASE) + stats cache invalidation

- Compose/Outbound Path:
  1. Client POST /compose → resolve SMTP settings
  2. Connect (STARTTLS 587 or SSL 465) → AUTH LOGIN/PLAIN
  3. Send DATA → Server 250 → Persist SENT row (direction=outbound)
  4. Optionally store raw for audit/troubleshooting

### 2) State Machines

- Interception Status (email_messages.interception_status):
  - NEW → (intercept) → HELD → (release) → RELEASED
  - NEW/HELD → (discard) → DISCARDED

- Message Status (email_messages.status):
  - PENDING → APPROVED/REJECTED → (on release) DELIVERED
  - SENT for outbound via composer

Legal transitions are enforced at the API handlers; invalid transitions respond 409/400.

### 3) Credential Sources & Precedence

- .env: Used by dev scripts (live_check.py, test_permanent_accounts.py) and optional startup preflight.
- Database (email_accounts): Source of truth for runtime workers and web actions (IMAP watchers, health checks, compose send).
- Encryption: passwords stored Fernet-encrypted using key.txt; never log plaintext.
- Precedence rule: Runtime → DB; Scripts → .env; Update DB via Accounts → Edit modal.

### 4) Provider Matrix & Connection Strategy

- Gmail: SMTP 587 STARTTLS, IMAP 993 SSL, App Password required (with spaces). Username=email.
- Hostinger: SMTP 465 SSL, IMAP 993 SSL. Username=email.
- Outlook: SMTP 587 STARTTLS, IMAP 993 SSL (App Password for 2FA).
- Yahoo: SMTP 465 SSL, IMAP 993 SSL.
- Rules of thumb:
  - 587 → STARTTLS (smtp_use_ssl=0, starttls=True)
  - 465 → SSL (smtp_use_ssl=1, no STARTTLS)
  - 993 → SSL (imap_use_ssl=1)

### 5) IMAP Watcher Lifecycle & Backoff

1. Load account config from DB → prefer imap_username else email_address
2. Establish connection:
   - SSL: imaplib.IMAP4_SSL(host, port=993)
   - STARTTLS: IMAP4(host, port=143) → starttls()
3. LOGIN user/pass; SELECT INBOX; IDLE (or noop polling fallback)
4. On new message signal: search new UIDs, FETCH metadata, MOVE to Quarantine
5. Persist HELD row (or update existing)
6. Heartbeat every N minutes; on errors: exponential backoff (e.g., 1s→2s→4s→... cap 5 min)
7. Always close gracefully on thread stop

Common auth failures:
- Wrong imap_username → fix via Edit modal (set to full email)
- STARTTLS vs SSL mismatch → ensure imap_use_ssl matches port
- Provider lockouts → ensure App Passwords / IMAP enabled

### 6) SMTP Send Pipeline Details

1. Resolve settings (smtp_host/port/use_ssl/username)
2. SSL (465): smtplib.SMTP_SSL; STARTTLS (587): smtplib.SMTP → ehlo → starttls → ehlo
3. AUTH (LOGIN/PLAIN via smtplib.login)
4. sendmail(from, to_list, data)
5. On success: INSERT SENT record; log audit SEND
6. On failure: map smtplib exceptions to user-facing messages; never log creds

### 7) Rule Engine (Keywords → Risk)

- Source: moderation_rules table (active rules)
- Keyword rules: comma-separated; case-insensitive match in subject/body
- Priority weighting → cumulative risk_score; threshold may auto-hold
- Fallback: default keyword set when DB rules absent

### 8) Error Taxonomy & Retries

- IMAP
  - AUTHENTICATIONFAILED → Immediate user action (update creds)
  - TIMEOUT/connection reset → Backoff and retry
  - MOVE unsupported → COPY+STORE + EXPUNGE fallback

- SMTP
  - SMTPAuthenticationError → user action (password/app password)
  - SMTPServerDisconnected / timeout → retry once after reconnect
  - STARTTLS failure on port 587 → ensure no SSL wrapper used

- DB/SQLite
  - database is locked → WAL mode + busy_timeout mitigate; retry after short sleep

### 9) Observability & Health

- app.log: structured logs for SMTP/IMAP events, auth failures, actions
- /healthz: DB OK, counts, worker heartbeats, security flags (no secrets)
- Stats cache: 2s TTL (unified counts), 10s TTL (latency percentiles)
- SSE: /stream/stats for live dashboard updates; fallback polling implemented

#### 9.1 JSON Log Quick Reference
- File locations: `logs/app.log` (text) and `logs/app.json.log` (structured)
- Sample record (`head -n1 logs/app.json.log`):
  ```json
  {"timestamp":"2025-10-15T02:55:14.512Z","level":"INFO","logger":"app.routes.interception","message":"[interception::release] success","email_id":123,"target":"INBOX","attachments_removed":false}
  ```
- Useful filters:
  ```bash
  # IMAP release failures
  jq 'select(.message|test("interception::release") and .level=="ERROR")' logs/app.json.log

  # SMTP connection issues grouped by host
  jq -r 'select(.message|test("smtp")) | .host' logs/app.json.log | sort | uniq -c
  ```

#### 9.2 Rate Limit Behaviour & Client Guidance
- Defaults (override via environment variables):
  | Endpoint | Default | Override Examples |
  |----------|---------|-------------------|
  | `/api/interception/release/<id>` | `30 per minute` | `RATE_LIMIT_RELEASE=20 per minute` |
  | `/api/email/<id>/edit` | `30 per minute` | `RATE_LIMIT_EDIT_REQUESTS=15`, `RATE_LIMIT_EDIT_WINDOW_SECONDS=60` |
  | `/api/fetch-emails` | `30 per minute` | `RATE_LIMIT_FETCH=45 per minute` |
- 429 handling pattern:
  ```javascript
  if (response.status === 429) {
    const retryAfter = Number(response.headers.get('Retry-After') || 1);
    toast.warning(`Too many requests – retry in ${retryAfter}s`);
    setTimeout(retryCall, retryAfter * 1000);
  }
  ```

#### 9.3 Prometheus / Grafana Starter Queries
- Error rate alert:
  ```promql
  rate(errors_total{component="imap_watcher"}[5m]) > 0.1
  ```
- Held backlog dashboard tile:
  ```promql
  emails_held_current
  ```
- IMAP watcher heartbeat drop:
  ```promql
  absent(imap_watcher_status == 1)
  ```
- Grafana tip: apply “Labels to fields” transform on `emails_held_current` to build per-account panels without extra queries.

### 10) Security Model (Operational View)

- CSRF: Flask-WTF; all forms include token; AJAX injects X-CSRFToken
- Rate limiting: 5/min on login; returns 429 with Retry-After
- Secrets: FLASK_SECRET_KEY in .env (64 hex); no plaintext secrets in logs
- Credential storage: Fernet (key.txt); rotate by re-encrypting after generating new key (plan)

### 11) Data Retention & Storage

- Raw email retention: configurable; large payloads can grow DB; consider offloading raw to filesystem with path pointer in DB for very large deployments
- Indices ensure queue views and counts stay fast (<20ms) on thousands of rows

### 12) Troubleshooting Playbooks

- Nothing works; /api/test/send-email 500:
  - Check SMTP proxy thread running (restart app); verify port 8587 not blocked

- IMAP auth failures for all accounts:
  - Verify DB-stored password (Edit modal), imap_use_ssl flag, username=email
  - Try scripts/live_check.py to validate provider outside watchers

- Gmail works, Hostinger fails:
  - Ensure SMTP 465 SSL (not 587), IMAP 993 SSL; confirm exact username

- Browser JS errors ($ is not defined):
  - Remove jQuery; use Bootstrap 5 Modal API only

### 13) From-Scratch Minimal Blueprint (If Rewriting)

- Core choices:
  - API: FastAPI or Flask (typed pydantic models if FastAPI)
  - SMTP proxy: aiosmtpd (async) + structured middleware; separate process/service
  - IMAP watcher: separate worker process with asyncio + imapclient/imaplib2
  - DB: SQLite initially; abstract via repository pattern for testability
  - Settings: pydantic-settings or dynaconf; single source of truth

- Modules:
  - accounts (CRUD, encrypted creds, health)
  - messages (store, edit, release, audit)
  - rules (CRUD, engine, scoring)
  - workers (smtp, imap)
  - web (dashboard UI) isolated from core libraries

- Principles:
  - Clear contracts between layers; no global DB_PATH
  - Pure functions where possible; dependency injection for IO
  - End-to-end integration tests behind dotenv-gated flag for live providers

- Migration path from current app:
  - Carve out standalone libs (db access, email parsing, rules)
  - Replace Flask route internals to call new libs
  - Port UI gradually; keep endpoints backward compatible

See docs/TECHNICAL_DEEP_DIVE.md for an exhaustive design and build guide.

## Additional Documentation

For more detailed information, see:

- **docs/STYLEGUIDE.md** - **MANDATORY** comprehensive style guide (colors, typography, components, patterns)
- **docs/INTERCEPTION_IMPLEMENTATION.md** - Technical details of email interception architecture
- **archive/docs/PERMANENT_TEST_ACCOUNTS.md** - Complete guide to permanent test accounts (superseded by CLAUDE.md)
- **archive/docs/WORKSPACE_CLEANUP_COMPLETE.md** - Previous workspace cleanup record

## Quick Reference Scripts

All scripts in `scripts/` directory:

**Email Account Management**:
- `test_permanent_accounts.py` - Test IMAP/SMTP connections (no DB changes)
- `setup_test_accounts.py` - Add/update accounts in database
- `verify_accounts.py` - Check database configuration

**Database Operations**:
- `verify_indices.py` - Verify database indices and query plans
- `migrations/*.py` - Database schema migrations

**Security & Validation**:
- `validate_security.py` - Run comprehensive security tests (4 tests)
- `../setup_security.ps1` - PowerShell security setup (Windows)
- `../setup_security.sh` - Bash security setup (Git Bash/WSL)

**System Checks**:
- `check_status.bat` - Quick Windows status check

---

## Architecture Decision Records (ADRs)

### ADR-001: Flask Singleton + SQLite Direct Access
**Decision**: Use Flask singleton pattern + direct SQLite access instead of SQLAlchemy ORM for simplicity
**Trade-off**: Perfect test isolation sacrificed for easier codebase understanding
**Impact**: Some tests fail in suite mode but pass individually (documented limitation)
**Documented**: `tests/conftest.py` lines 3-13

### ADR-002: Phase 1B Blueprint Migration Strategy
**Decision**: Gradual extraction of routes from `simple_app.py` monolith to `app/routes/*` blueprints
**Status**: In progress - auth, dashboard, stats, moderation, interception extracted
**Remaining**: Email viewer, accounts, compose, inbox routes still in monolith
**Impact**: Tests using old import paths fail until migration complete

### ADR-003: IMAP-Only Interception (Sieve Deprecated)
**Decision**: Focus on IMAP IDLE/MOVE interception, deprecate Sieve protocol support
**Rationale**: Sieve server support rare, IMAP universal
**Implementation**: `app/services/imap_watcher.py`, `app/routes/interception.py`
**Documentation**: `INTERCEPTION_IMPLEMENTATION.md`

---

**Remember**: This application IS working. If it's not:

1. Check `python simple_app.py` is running
2. Access http://localhost:5000
3. Verify accounts configured with `python scripts/verify_accounts.py`
4. Check `app.log` for errors
5. Test connections with `python scripts/test_permanent_accounts.py`
6. Run working tests: `python -m pytest tests/interception/ -v`
