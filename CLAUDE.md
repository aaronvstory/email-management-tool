# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Email Management Tool** is a Python Flask application for local email interception, moderation, and management. Dev-focused; runs entirely on localhost with SQLite—no cloud services, no Docker required.

**Version**: 2.8
**Status**: 🟢 Fully functional — SMTP proxy running; IMAP watchers using hybrid IDLE+polling strategy; core UI accessible.
**Last Updated**: October 18, 2025

### Recent Major Updates
- ✅ **Test Coverage Milestone** - 138/138 tests passing, 36% coverage (was 27%), pre-commit hooks enabled
- ✅ **Hybrid IMAP Strategy** - IDLE+polling hybrid prevents timeout issues (See: [docs/HYBRID_IMAP_STRATEGY.md](docs/HYBRID_IMAP_STRATEGY.md))
- ✅ **Security Hardening** - CSRF protection, rate limiting, strong SECRET_KEY generation (See: [docs/SECURITY.md](docs/SECURITY.md))
- ✅ **Blueprint Modularization** - Routes now in app/routes/* (9 active blueprints)
- ✅ **Workspace Cleanup** - Archived 21+ redundant files, organized documentation

## At-a-Glance

| Component            | Details                                                           |
| -------------------- | ----------------------------------------------------------------- |
| **Web Dashboard**    | http://localhost:5000 (admin / admin123)                          |
| **SMTP Proxy**       | localhost:8587                                                    |
| **Database**         | SQLite (`email_manager.db`) - local only                          |
| **Encryption**       | Fernet symmetric (`key.txt`)                                      |
| **Primary Launcher** | `EmailManager.bat` (menu) or `launch.bat` (quick)                 |
| **Test Accounts**    | Gmail (ndayijecika@gmail.com), Hostinger (mcintyre@corrinbox.com) |

⚠️ **Security Note**: Test accounts are for **development/testing only**. Never use in production.

## Quick Start

### Prerequisites
- Python 3.9+ (tested with 3.13)
- Windows environment (batch scripts)
- Email accounts with App Passwords configured

### Starting the Application

```bash
# Recommended: Professional launcher
EmailManager.bat

# Quick start
launch.bat

# Direct Python execution
python simple_app.py
```

**Access Points**:
- Web Dashboard: http://localhost:5000
- Default Login: `admin` / `admin123`

### Restarting After Port Conflicts

```bash
# Automatic cleanup and restart
python cleanup_and_start.py

# Manual cleanup
tasklist | findstr python.exe
taskkill /F /PID <pid>
python simple_app.py
```

## 🔑 Test Accounts (DO NOT MODIFY)

**CRITICAL**: These are the ONLY two accounts with confirmed working credentials.

### Account 1: Gmail - NDayijecika (Primary)
- **Email**: ndayijecika@gmail.com
- **SMTP**: smtp.gmail.com:587 (STARTTLS)
- **IMAP**: imap.gmail.com:993 (SSL)
- **Status**: ✅ Live checks OK

### Account 2: Hostinger - Corrinbox (Secondary)
- **Email**: mcintyre@corrinbox.com
- **SMTP**: smtp.hostinger.com:465 (SSL direct)
- **IMAP**: imap.hostinger.com:993 (SSL)
- **Status**: ⚠️ Check credentials if failing

**Smart Detection**: The app auto-detects SMTP/IMAP settings from email domain. Gmail uses port 587 STARTTLS, Hostinger uses port 465 SSL.

## File Organization

```
Email-Management-Tool/
├── simple_app.py                    # Main application (~918 lines)
├── email_manager.db                 # SQLite database
├── key.txt                          # Encryption key (CRITICAL)
├── requirements.txt                 # Dependencies
├── EmailManager.bat                 # Primary launcher
├── CLAUDE.md                        # This file
├── app/
│   ├── routes/                      # 9 Blueprint modules
│   ├── services/                    # Stats, audit, IMAP workers
│   └── utils/                       # db.py, crypto.py, metrics
├── docs/                            # Comprehensive documentation
│   ├── ARCHITECTURE.md              # System architecture
│   ├── DATABASE_SCHEMA.md           # Database design
│   ├── SECURITY.md                  # Security configuration
│   ├── STYLEGUIDE.md                # UI/UX standards (MUST FOLLOW)
│   ├── HYBRID_IMAP_STRATEGY.md      # IMAP implementation
│   └── reports/                     # Analysis reports
├── tests/                           # Test suite (pytest)
├── scripts/                         # Utility scripts
├── archive/                         # Historical files
└── static/ & templates/             # Frontend assets
```

## Quick Reference

### Essential Commands

```bash
# Start application
python simple_app.py

# Run tests
python -m pytest tests/ -v

# Test specific file
python -m pytest tests/test_intercept_flow.py -v

# Security validation
python -m scripts.validate_security

# Test permanent accounts
python scripts/test_permanent_accounts.py

# Health check
curl http://localhost:5000/healthz
```

### Key API Endpoints

```
# Authentication
GET  /login                          # Login page
POST /login                          # Authenticate

# Dashboard
GET  /dashboard                      # Main dashboard

# Interception
GET  /api/interception/held          # List HELD messages
POST /api/interception/release/<id>  # Release to inbox
POST /api/interception/discard/<id>  # Discard message
POST /api/email/<id>/edit            # Edit email

# Health & Monitoring
GET  /healthz                        # Health check
GET  /metrics                        # Prometheus metrics
```

## AI-Assisted Development

### Active MCP Servers
This project uses Model Context Protocol (MCP) servers for enhanced development capabilities:

**Primary Tools**:
- **Serena** - Semantic code intelligence for Python
  - Symbol-aware code navigation and editing
  - Safe refactoring with dependency tracking
  - Dashboard: http://127.0.0.1:24282/dashboard/index.html
  - Use for: Finding functions/classes, analyzing imports, project-wide changes
- **Desktop Commander** - File system and process management
  - File operations, directory traversal, search capabilities
  - Process management and system commands
  - Use for: File I/O, bulk operations, system diagnostics
- **Memory** - Knowledge graph for persistent project context
- **Sequential Thinking** - Complex multi-step analysis and planning
- **Context7** - Library documentation lookup
- **Exa/Perplexity** - Web research and current information

**Disabled Servers** (to save 46k tokens context):
- ❌ chrome-devtools (browser automation - enable manually when needed)
- ❌ shadcn-ui (React components - not applicable to Flask project)

### `/sp` Command (SuperPower Orchestration)
Primary command for intelligent task orchestration across all MCP servers.

**Usage**:
```bash
/sp [task description]
```

**Examples**:
```bash
/sp analyze the SMTP proxy authentication flow
/sp refactor IMAP watcher to use better error handling  
/sp add comprehensive logging to interception.py
/sp find all SQL queries and check for injection risks
```

**Auto-Detection**:
- Code analysis → Activates Serena MCP (semantic understanding)
- Research tasks → Activates Exa/Perplexity (web search)
- File operations → Uses Desktop Commander (file system)
- Library questions → Uses Context7 (documentation lookup)

**Features**:
- Automatically spawns expert sub-agents for complex tasks
- Coordinates between multiple MCP servers intelligently
- Saves research findings to `.claude/research/` for reuse
- 87% token reduction through intelligent caching

## Development Guidelines

### State Management
- **Database Access**: Always use `app.utils.db.get_db()` context manager for thread-safe connections
- **Row Factory**: Enables dict-like access to query results (`row['column']` instead of `row[0]`)
- **Thread Safety**: SQLite WAL mode + busy_timeout handles concurrent access from multiple threads
- **Caching**: Stats endpoints use TTL-based caching (2-5 seconds) to reduce database load

### UI Development
**⚠️ ALWAYS consult `docs/STYLEGUIDE.md` before making ANY UI changes!**

Key principles:
- Dark theme by default (consistent backgrounds, no white flashes)
- Use `.input-modern` class for all inputs
- Bootstrap 5.3 toasts (not browser alerts)
- Confirmation prompts only for destructive actions
- Background: `background-attachment: fixed` to prevent white screen on scroll

### Database Operations
Always use `row_factory` for dict-like access:

```python
from app.utils.db import get_db

with get_db() as conn:
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM email_messages WHERE status=?", ('PENDING',)).fetchall()
    for row in rows:
        print(row['subject'])  # Dict access, not row[2]
```

### Blueprint Structure
Routes are organized in `app/routes/`:
- `auth.py` - Authentication
- `dashboard.py` - Dashboard views
- `stats.py` - Statistics APIs
- `moderation.py` - Rule management
- `interception.py` - Email hold/release/edit
- `emails.py` - Email CRUD
- `accounts.py` - Account management
- `inbox.py` - Inbox viewer
- `compose.py` - Email composition

## Current Capabilities

✅ Full email interception (SMTP + IMAP)
✅ Multi-account management with smart detection
✅ Email editing before approval
✅ Dashboard with live stats
✅ Risk scoring and filtering
✅ Complete audit trail
✅ Attachment handling
✅ Real-time monitoring
✅ Encrypted credential storage
✅ **Modern toast notification system** - No more browser alerts!
✅ **Production-ready security** - CSRF, rate limiting, strong SECRET_KEY

## Known Limitations

✅ **Test Coverage**: 36% code coverage, 138/138 tests passing (target: 50%+)
⚠️ **SMTP Proxy**: Must be running (check /api/smtp-health)
⚠️ **Port Conflicts**: May need cleanup_and_start.py if port 8587 is in use

## Troubleshooting Quick Reference

**Gmail Authentication Failed**
→ Use App Password (with spaces), verify 2FA enabled

**Port Already in Use**
→ `python cleanup_and_start.py` or manually kill python.exe processes

**Database Schema Mismatch**
→ Check docs/DATABASE_SCHEMA.md for migration scripts

**UI Styling Issues**
→ Consult docs/STYLEGUIDE.md for proper patterns

## Detailed Documentation

For deeper technical information, see:

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design
- **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - Database design and indices
- **[docs/SECURITY.md](docs/SECURITY.md)** - Security configuration and validation
- **[docs/STYLEGUIDE.md](docs/STYLEGUIDE.md)** - UI/UX standards (MANDATORY)
- **[docs/HYBRID_IMAP_STRATEGY.md](docs/HYBRID_IMAP_STRATEGY.md)** - IMAP implementation
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development workflow
- **[docs/TESTING.md](docs/TESTING.md)** - Testing strategy
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[docs/TECHNICAL_DEEP_DIVE.md](docs/TECHNICAL_DEEP_DIVE.md)** - Architecture deep dive

---

**Remember**: This application IS working. If it's not:
1. Check `python simple_app.py` is running
2. Access http://localhost:5000
3. Verify accounts configured with `python scripts/verify_accounts.py`
4. Check `logs/app.log` for errors
5. Test connections with `python scripts/test_permanent_accounts.py`
