# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Email Management Tool is a Python Flask application for email interception, moderation, and management. It runs locally on Windows with SQLite (no Docker required) and provides SMTP proxy + IMAP monitoring for holding emails before delivery.

**Version**: 2.8 | **Python**: 3.9+ (tested with 3.13) | **OS**: Windows
**Status**: Partially functional — requires SMTP proxy running and valid IMAP credentials in DB

## Quick Start Commands

### Starting the Application
```bash
# PowerShell management (recommended)
.\manage.ps1 start          # Start with management console
.\manage.ps1 stop           # Stop application
.\manage.ps1 status         # Check status

# Direct Python execution
python simple_app.py        # Run Flask app directly

# Windows batch launchers
EmailManager.bat            # Menu-driven launcher
launch.bat                  # Quick start with browser

# Access: http://localhost:5000 (admin/admin123)
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites (recommended)
python -m pytest tests/interception/ -v        # 80% pass rate
python -m pytest tests/test_intercept_flow.py -v  # 100% pass

# Test account connections (no DB changes)
python scripts/test_permanent_accounts.py

# Verify database configuration
python scripts/verify_accounts.py

# Security validation (must pass before production)
python -m scripts.validate_security
```

### Development Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Security setup (generates strong SECRET_KEY)
.\setup_security.ps1

# Database operations
python scripts/verify_indices.py                          # Check indices
python scripts/migrations/20251001_add_interception_indices.py  # Run migrations

# Format code (when black is installed)
black app tests --line-length 88

# Type checking (when mypy is installed)
mypy app
```

## Architecture

### Core Structure
```
simple_app.py (~918 lines)     # Main Flask bootstrap + services
app/
├── routes/                    # Flask blueprints (9 modules, ~1,300 lines total)
│   ├── auth.py               # Login/logout
│   ├── dashboard.py          # Main dashboard views
│   ├── interception.py       # Email hold/release/edit API
│   ├── accounts.py           # Account management + IMAP control
│   ├── emails.py             # Email queue/viewer
│   └── stats.py              # Statistics + SSE streaming
├── services/
│   ├── imap_watcher.py       # IMAP monitoring service
│   └── stats.py              # Cached statistics (2s TTL)
├── utils/
│   ├── db.py                 # SQLite layer (dependency-injectable)
│   ├── crypto.py             # Fernet encryption for credentials
│   └── email_helpers.py      # SMTP/IMAP detection + testing
└── models/
    └── simple_user.py        # Flask-Login user model
```

### Key Services
- **SMTP Proxy**: Port 8587 (aiosmtpd) - intercepts outgoing emails
- **IMAP Watchers**: Per-account threads monitoring INBOX
- **Web Dashboard**: Port 5000 - Flask with Bootstrap 5.3 UI
- **SQLite DB**: `email_manager.db` with WAL mode + optimized indices

### Email Processing Flow
```
1. SMTP Intercept (8587) → Parse → Risk Score → Store as PENDING/HELD
2. IMAP Monitor → Detect new → MOVE to Quarantine → Store as HELD
3. Dashboard Review → Optional Edit → Release (APPEND to INBOX) or Discard
4. Audit logging at each step
```

## Database Schema

### Critical Tables
- `email_accounts` - Encrypted IMAP/SMTP credentials per account
- `email_messages` - All intercepted emails with audit trail
  - Status: PENDING/APPROVED/REJECTED/SENT/DELIVERED
  - Interception: HELD/RELEASED/DISCARDED
- `users` - Authentication with bcrypt hashing
- `moderation_rules` - Keyword-based auto-hold rules

### Performance Indices (6 optimized)
```sql
idx_email_messages_interception_status
idx_email_messages_status
idx_email_messages_account_status
idx_email_messages_account_interception
idx_email_messages_direction_status
idx_email_messages_original_uid
```

## API Endpoints

### Core Interception API
```
GET  /api/interception/held            # List held messages
POST /api/interception/release/<id>    # Release to inbox
POST /api/interception/discard/<id>    # Discard message
POST /api/email/<id>/edit              # Edit subject/body
GET  /healthz                           # Health check (5s cache)
```

### Account Management
```
POST /api/detect-email-settings        # Auto-detect SMTP/IMAP
POST /api/accounts/<id>/monitor/start  # Start IMAP watcher
POST /api/accounts/<id>/monitor/stop   # Stop IMAP watcher
GET  /api/accounts/<id>/health         # Test connection
```

### Statistics & Monitoring
```
GET  /api/stats                        # Dashboard stats (2s cache)
GET  /api/unified-stats                # Aggregated counts (5s cache)
GET  /stream/stats                     # SSE live updates
```

## Configuration

### Environment Variables (.env)
```bash
FLASK_SECRET_KEY=<64-char-hex>        # Required for production
DB_PATH=email_manager.db              # SQLite database path
ENABLE_WATCHERS=1                      # Enable IMAP monitoring
SMTP_PROXY_PORT=8587                  # SMTP intercept port
FLASK_PORT=5000                        # Web dashboard port

# Test accounts (development only)
GMAIL_ADDRESS=ndayijecika@gmail.com
GMAIL_PASSWORD=<app-password>
HOSTINGER_ADDRESS=mcintyre@corrinbox.com
HOSTINGER_PASSWORD=<app-password>
```

### Provider Configuration
| Provider | SMTP Settings | IMAP Settings |
|----------|--------------|---------------|
| Gmail | smtp.gmail.com:587 (STARTTLS) | imap.gmail.com:993 (SSL) |
| Hostinger | smtp.hostinger.com:465 (SSL) | imap.hostinger.com:993 (SSL) |
| Outlook | smtp.outlook.com:587 (STARTTLS) | imap.outlook.com:993 (SSL) |

**Note**: Gmail/Outlook require App Passwords (not regular passwords)

## UI/UX Guidelines

**CRITICAL**: Follow `docs/STYLEGUIDE.md` for all UI changes

### Key Patterns
- **Dark theme**: `#1a1a1a` backgrounds, gradient cards
- **Inputs**: Use `.input-modern` class (dark background)
- **Buttons**: 42px standard height, consistent spacing
- **Toasts**: Use `showSuccess()`, `showError()`, not browser alerts
- **Fixed background**: `background-attachment: fixed` prevents white flash

## Development Workflow

### Adding Features
1. Check if route exists in `app/routes/` blueprints
2. For new endpoints, add to appropriate blueprint
3. Database changes: Add migration in `scripts/migrations/`
4. UI changes: Follow `docs/STYLEGUIDE.md` patterns
5. Add tests in corresponding `tests/` directory

### Blueprint Organization
- `auth.py` - Authentication (login/logout)
- `dashboard.py` - Main dashboard views
- `interception.py` - Email hold/release operations
- `accounts.py` - Account CRUD + IMAP control
- `emails.py` - Email queue and viewer
- `stats.py` - Statistics and SSE streaming
- `compose.py` - Email composition
- `inbox.py` - Unified inbox view
- `moderation.py` - Rule management

### Security Checklist
1. Run `.\setup_security.ps1` to generate strong SECRET_KEY
2. Validate with `python -m scripts.validate_security` (4 tests must pass)
3. Never commit `.env`, `key.txt`, or `email_manager.db`
4. Change default admin password in production

## Known Issues & Limitations

### Test Infrastructure (43.6% pass rate)
- **Root cause**: Import path changes from Phase 1B modularization
- **Workaround**: Use `python -m pytest tests/interception/ -v` (80% pass)
- **Fix needed**: Create `tests/conftest.py` with Flask fixtures

### Architecture Decisions
- **ADR-001**: Direct SQLite access (no ORM) for simplicity
- **ADR-002**: Gradual blueprint migration (9/15 routes migrated)
- **ADR-003**: IMAP-only interception (Sieve deprecated)

### Current Gaps
- 62 tests fail due to missing fixtures/imports
- 130 LOC duplicated across blueprints (needs consolidation)
- No automated CI/CD pipeline configured

## Troubleshooting

### Common Issues
```bash
# Port already in use
netstat -an | findstr :8587
taskkill /F /PID <pid>

# Gmail auth failed
# → Use App Password with spaces: "xxxx xxxx xxxx xxxx"
# → Enable 2FA and IMAP in Gmail settings

# Database locked
# → WAL mode + busy_timeout should prevent this
# → If persists, restart application

# IMAP watcher not starting
# → Check credentials in DB via Accounts page
# → Verify with: python scripts/test_permanent_accounts.py
```

### Health Check
```bash
curl http://localhost:5000/healthz

# Expected response:
{
  "ok": true,
  "db": "ok",
  "held_count": 0,
  "released_24h": 0,
  "median_latency_ms": null,
  "workers": [],
  "security": {
    "secret_key_configured": true,
    "csrf_enabled": true
  }
}
```

## Additional Documentation
- `docs/STYLEGUIDE.md` - **MANDATORY** UI/UX standards
- `docs/INTERCEPTION_IMPLEMENTATION.md` - Technical architecture
- `README.md` - User-facing setup and features
- `AGENTS.md` - Repository guidelines and conventions
- `.env.example` - Configuration template