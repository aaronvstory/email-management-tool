# CLAUDE.md

This file provides essential guidance to Claude Code when working with code in this repository. For detailed documentation, see the `docs/` directory.

## Project Overview

**Email Management Tool** - Production-ready Python Flask application for email interception, moderation, and management.

- **Version**: 2.7 (Production Ready)
- **Status**: ✅ WORKING AND DEPLOYED
- **Stack**: Flask + SQLite + SMTP/IMAP
- **Environment**: Windows localhost-only
- **Python**: 3.9+ (tested with 3.13)

## Quick Reference

| Component | Value |
|-----------|-------|
| **Web Dashboard** | http://localhost:5000 |
| **Default Login** | admin / admin123 |
| **SMTP Proxy** | localhost:8587 |
| **Database** | SQLite (email_manager.db) |
| **Encryption Key** | key.txt (Fernet) |
| **Main Script** | simple_app.py |
| **Launcher** | EmailManager.bat |

## Documentation Structure

- **[docs/SECURITY.md](docs/SECURITY.md)** - Security setup, validation, deployment checklists
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development workflow, testing, UI guidelines
- **[docs/API.md](docs/API.md)** - Complete API reference and endpoints
- **[docs/TEST_ACCOUNTS.md](docs/TEST_ACCOUNTS.md)** - Test accounts configuration
- **[docs/STYLEGUIDE.md](docs/STYLEGUIDE.md)** - ⚠️ MANDATORY UI/UX standards

## Current Architecture

### Core Components

**`simple_app.py`** (918 lines) - Application bootstrap:
- Flask web server with Flask-Login authentication
- SMTP proxy (aiosmtpd, port 8587)
- IMAP monitoring threads (per-account)
- SQLite with encrypted credentials

### Blueprint Organization

| Blueprint | Location | Purpose |
|-----------|----------|---------|
| auth | app/routes/auth.py | Login/logout |
| dashboard | app/routes/dashboard.py | Main dashboard |
| stats | app/routes/stats.py | Statistics API with caching |
| moderation | app/routes/moderation.py | Rules management |
| interception | app/routes/interception.py | Hold/release/edit emails |
| emails | app/routes/emails.py | Email viewer and queue |
| accounts | app/routes/accounts.py | Account management |
| inbox | app/routes/inbox.py | Unified inbox |
| compose | app/routes/compose.py | Email composition |

### Key Services

- **app/utils/db.py** - Dependency-injectable database layer
- **app/utils/crypto.py** - Fernet encryption for credentials
- **app/services/audit.py** - Audit logging service
- **app/services/stats.py** - Cached statistics (2-5s TTL)
- **app/workers/imap_startup.py** - IMAP watcher threads

## Database Schema

### Primary Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| email_accounts | Account credentials | imap/smtp settings (encrypted) |
| email_messages | Intercepted emails | status, interception_status, risk_score |
| users | Authentication | username, password_hash (bcrypt) |
| audit_log | Action tracking | action, timestamp, user |

### Performance Indices

```sql
idx_email_messages_interception_status
idx_email_messages_status
idx_email_messages_account_status
idx_email_messages_account_interception
idx_email_messages_direction_status
idx_email_messages_original_uid
```

## Email Processing Flow

```
1. Inbound Email → SMTP Proxy (8587) or IMAP IDLE
2. Risk Assessment → Store as PENDING/HELD
3. Dashboard Review → Edit if needed
4. Release/Discard → APPEND to INBOX or mark DISCARDED
5. Audit Log → Track all actions
```

## Critical Configuration

### Required Files

- **`.env`** - Environment variables (create from .env.example)
- **`key.txt`** - Encryption key (auto-generated on first run)
- **`email_manager.db`** - SQLite database

### Essential Environment Variables

```bash
FLASK_SECRET_KEY=<64-char-hex>  # Run setup_security.ps1 to generate
DB_PATH=email_manager.db
ENABLE_WATCHERS=1  # IMAP monitoring threads
```

## Test Accounts

Two permanent test accounts configured (see [docs/TEST_ACCOUNTS.md](docs/TEST_ACCOUNTS.md)):

1. **Gmail**: ndayijecika@gmail.com (ID: 3)
2. **Hostinger**: mcintyre@corrinbox.com (ID: 2)

Both require app-specific passwords set via `.env` file.

## Current State (Oct 12, 2025)

### Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Monolith Size | 918 lines | ✅ |
| Blueprint Coverage | 100% | ✅ |
| Security Validation | 4/4 tests passing | ✅ |
| Critical Test Path | 3/3 passing | ✅ |
| CSRF + Rate Limiting | Enabled | ✅ |

### Recent Completions

- ✅ Security hardening (CSRF, rate limiting, strong keys)
- ✅ Blueprint modularization (9 active blueprints)
- ✅ Account edit modal with API
- ✅ Toast notification system (no browser alerts)
- ✅ CI with GitHub Actions on Windows
- ✅ Documentation reorganization for performance

### Known Issues

1. **Test Infrastructure**: Some tests fail due to import path changes from Phase 1B
2. **Helper Duplication**: ~130 LOC duplicated across blueprints
3. **Test Fixtures**: Missing `conftest.py` for Flask fixtures

## Development Priorities

### Immediate (This Week)
1. Fix test infrastructure - Add `conftest.py` with Flask fixtures
2. Consolidate helper functions to `app/utils/`
3. Update import paths for Phase 1B compatibility

### Next Sprint
1. Complete remaining blueprint migrations
2. Add integration test suite with real accounts
3. Set up proper CI/CD pipeline

## Security Essentials

**⚠️ CRITICAL**: Before production deployment:

1. Run `.\setup_security.ps1` to generate strong SECRET_KEY
2. Run `python -m scripts.validate_security` (all 4 tests must pass)
3. Change default admin password
4. Review [docs/SECURITY.md](docs/SECURITY.md) deployment checklist

## Quick Commands

### Start Application
```bash
EmailManager.bat        # Menu-driven launcher
launch.bat             # Quick start
python simple_app.py   # Direct execution
```

### Testing
```bash
python -m pytest tests/test_intercept_flow.py -v  # Recommended
python scripts/test_permanent_accounts.py         # Test connections
python scripts/validate_security.py               # Security validation
```

### Database
```bash
python scripts/verify_indices.py                  # Check indices
python scripts/migrations/20251001_add_interception_indices.py
```

## File Structure

```
Email-Management-Tool/
├── simple_app.py              # Main application
├── app/
│   ├── routes/               # Blueprint modules
│   ├── utils/                # Shared utilities
│   ├── services/             # Business logic
│   └── workers/              # Background threads
├── docs/                      # Detailed documentation
│   ├── SECURITY.md          # Security guide
│   ├── DEVELOPMENT.md       # Development guide
│   ├── API.md               # API reference
│   ├── TEST_ACCOUNTS.md    # Test accounts
│   └── STYLEGUIDE.md        # UI/UX standards
├── templates/                 # Jinja2 templates
├── static/                    # JS/CSS assets
├── scripts/                   # Utility scripts
├── tests/                     # Test suite
└── archive/                   # Historical files
```

## Architecture Decision Records

### ADR-001: Flask + SQLite Direct Access
**Decision**: Direct SQLite instead of ORM for simplicity
**Trade-off**: Test isolation for codebase clarity
**Impact**: Some tests fail in suite but pass individually

### ADR-002: Blueprint Migration Strategy
**Status**: Phase 1B/1C complete (9 blueprints active)
**Remaining**: Test infrastructure updates for new imports

### ADR-003: IMAP-Only (No Sieve)
**Decision**: IMAP IDLE/MOVE for interception
**Rationale**: Universal support vs rare Sieve availability

## Important Constraints

- **NO POP3**: Database schema only supports IMAP/SMTP
- **Windows-only**: Batch scripts and path conventions
- **Localhost-only**: Not designed for remote access
- **Dark Theme**: All UI must follow docs/STYLEGUIDE.md

## Support & Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Gmail auth failed | Use App Password with spaces |
| Port in use | `taskkill /F /PID <pid>` |
| DB schema error | Run migrations in scripts/migrations/ |
| White backgrounds | Check docs/STYLEGUIDE.md compliance |

### Getting Help

1. Check relevant docs in `docs/` directory
2. Review `app.log` for detailed errors
3. Run diagnostic scripts in `scripts/`
4. Test with permanent accounts first

## What's Working

✅ Email interception (SMTP/IMAP)
✅ Multi-account with smart detection
✅ Edit modal with API
✅ Dashboard with live stats
✅ Risk scoring and rules
✅ Audit trail
✅ Encrypted credentials
✅ Toast notifications
✅ Production security
✅ CI with GitHub Actions

---

**Remember**: This application is production-ready. If issues arise:
1. Verify `python simple_app.py` is running
2. Check http://localhost:5000
3. Run `python scripts/verify_accounts.py`
4. Review `app.log` for errors