# Development Guide

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

## Development Commands

### Running Tests

```bash
# Fast, targeted path (recommended for local)
python -m pytest tests/test_intercept_flow.py -v

# Full suite (pending migration; may include quarantined tests)
python -m pytest tests/ -v --tb=short

# Test specific file
python -m pytest tests/test_intercept_flow.py -v

# Test single function
python -m pytest tests/test_intercept_flow.py::test_fetch_stores_uid_and_internaldate -v

# Run with detailed output
python -m pytest tests/ -v --tb=short

# Exclude broken imports (until Phase 1B migration complete)
python -m pytest tests/ -v --ignore=tests/integration --ignore=tests/performance --ignore=tests/unit/backend/test_smtp_proxy.py --ignore=tests/unit/test_account_management.py
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
# Format
black .

# Lint
pylint app simple_app.py

# Type check
mypy .
# (Optional) Pyright if installed
# pyright
```

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
   - **Use toast notifications** (see Toast Notifications section below for details)
6. Test UI checklist (see below)
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

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py                    # Pytest configuration
├── test_unified_stats.py          # Dashboard stats (2 tests, all pass)
├── test_latency_stats.py          # Latency metrics (4 tests, 2 pass in suite)
├── test_intercept_flow.py         # Interception lifecycle (3 tests, all pass) ✅ NEW
└── TEST_ISOLATION_STATUS.md       # Known test limitations
```

### Test Coverage
- ✅ **Interception Lifecycle** (test_intercept_flow.py) - 100% pass rate (3/3)
  - `test_fetch_stores_uid_and_internaldate` - Verifies IMAP fetch stores UID and server timestamp
  - `test_manual_intercept_moves_and_latency` - Validates HELD status with remote MOVE and latency calculation
  - `test_release_sets_delivered` - Confirms RELEASED/DELIVERED transition after email edit
- ✅ **Dashboard Stats** (test_unified_stats.py) - 100% pass rate (2/2)
- ⚠️ **Latency Metrics** (test_latency_stats.py) - 50% pass rate (2/4 in suite, all pass individually)

### Running Tests

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

## Architecture Constraints

**NO POP3 SUPPORT**: The database schema only supports IMAP/SMTP. Do not add POP3 code:

- `email_accounts` table has no `pop3_*` columns
- Only `imap_host`, `imap_port`, `smtp_host`, `smtp_port` exist
- Any POP3 references will cause SQLite column errors

## Configuration & Settings

### Environment Variables

**`.env` file** (not committed) - Optional configuration overrides:
- `DB_PATH` - Override default SQLite database path
- `ENABLE_WATCHERS` - Enable/disable IMAP monitoring threads (default: 1)
- `ENABLE_LIVE_EMAIL_TESTS` - Gate live email tests (default: 0)
- `LIVE_EMAIL_ACCOUNT` - Which test account to use (gmail or hostinger)
- `GMAIL_ADDRESS`, `GMAIL_PASSWORD` - Gmail test credentials
- `HOSTINGER_ADDRESS`, `HOSTINGER_PASSWORD` - Hostinger test credentials
- `FLASK_SECRET_KEY` - Strong 64-char hex for session security

**`.env.example`** - Template with all configuration options and credential placeholders

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

## Troubleshooting

### Common Issues

**Gmail Authentication Failed**
→ Use App Password (with spaces), verify 2FA enabled

**Port Already in Use**
→ `netstat -an | findstr :8587` then `taskkill /F /PID <pid>`

**Database Schema Mismatch**
→ Run `python scripts/migrate_database.py`

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

## Threading Model

- **Main Thread**: Flask web server (port 5000)
- **SMTP Thread**: Email interception proxy (port 8587, daemon)
- **IMAP Threads**: Per-account monitoring (daemon, auto-reconnect)
  - Controlled by `ENABLE_WATCHERS` env var (default: enabled)
  - Started via `app/workers/imap_startup.py::start_imap_watchers()`
  - All threads share SQLite DB; WAL + busy_timeout mitigate contention

## Gmail Setup (For Adding New Accounts)

1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. **Use password WITH spaces**: `xxxx xxxx xxxx xxxx`
4. Enable IMAP in Gmail settings
5. SMTP: `smtp.gmail.com:587` (STARTTLS)
6. IMAP: `imap.gmail.com:993` (SSL)