# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Email Management Tool is a Python Flask application for intercepting, moderating, and managing emails across multiple accounts. It provides a web dashboard for reviewing emails before they're sent, with full audit trails and modification capabilities. The application features real-time email monitoring, encrypted credential storage, and a modern responsive UI with enhanced visibility and navigation.

## Development Commands

### Starting the Application
```bash
# Main application (stable, single-file implementation)
python simple_app.py

# Windows quick start
start.bat

# PowerShell management
.\manage.ps1 start

# Access points after startup:
# - Web Dashboard: http://localhost:5000
# - SMTP Proxy: localhost:8587
# - Default login: admin / admin123
```

### Database Setup
```bash
# Initialize database with test accounts
python populate_test_accounts.py

# This creates:
# - Admin user (admin/admin123)
# - Gmail Test Account
# - Hostinger Account
# - Database tables with proper schema
```

### Testing Commands
```bash
# Test Gmail integration with app passwords
python test_gmail_integration.py

# Test complete workflow (intercept → modify → release)
python test_complete_workflow.py

# Run email diagnostics for all configured accounts
python email_diagnostics.py

# Test SMTP proxy functionality
python test_smtp_proxy.py

# Verify account credentials
python verify_app_password.py
```

### Management Commands (PowerShell)
```powershell
.\manage.ps1 status    # Check application status
.\manage.ps1 start     # Start application
.\manage.ps1 stop      # Stop application
.\manage.ps1 restart   # Restart application
.\manage.ps1 backup    # Create backup
.\manage.ps1 logs      # View logs
```

## Architecture Overview

### Core Components

**simple_app.py** (Main Application - 1492 lines)
- Flask web server with Bootstrap 5.3 UI
- SMTP proxy server (aiosmtpd) running on port 8587
- SQLite database (`email_manager.db`) for email storage and user management
- Flask-Login for authentication with role-based access
- Threading for SMTP proxy and IMAP monitoring
- Fernet encryption for credential storage (key in `key.txt`)

**Key Database Tables**
- `users` - Authentication and role management (username, email, password_hash, role)
- `email_messages` - Intercepted emails with status tracking (PENDING/APPROVED/REJECTED/SENT)
- `email_accounts` - Configured email accounts with encrypted passwords (IMAP/SMTP settings)
- `moderation_rules` - Automated filtering rules (rule_name, condition_field, action, priority)
- `audit_logs` - Complete action history with user tracking and IP logging

### Email Processing Flow
1. **Interception**: SMTP proxy on port 8587 captures outgoing emails
2. **Storage**: Emails saved to SQLite with status='PENDING'
3. **Risk Assessment**: Automatic scoring based on content/rules
4. **Dashboard Review**: Web UI for viewing/modifying emails
5. **Action**: Approve (send), Reject (block), or Hold
6. **Release**: Modified emails sent via configured SMTP relay

### Multi-Account Architecture
- Each email account has separate IMAP/SMTP configurations
- Credentials encrypted using Fernet encryption
- Per-account monitoring threads for IMAP
- Account-specific diagnostics and testing

## Key Routes & Endpoints

### Web Routes
- `/` - Login page
- `/dashboard` - Main dashboard with statistics
- `/dashboard/<tab>` - Tabbed navigation (overview, emails, accounts, diagnostics, rules)
- `/emails` - Email queue management
- `/emails/<id>` - Individual email detail/edit
- `/accounts` - Email account management
- `/accounts/add` - Add new email account
- `/diagnostics` - Connectivity testing
- `/rules` - Moderation rules configuration

### API Endpoints
- `/api/stats` - Real-time statistics
- `/api/emails` - Email CRUD operations
- `/api/accounts/<account_id>` - Get account details with decrypted passwords
- `/api/diagnostics/<account_id>` - Per-account connection testing
- `/api/test-connection/<type>` - Test IMAP/SMTP connections (POST)
- `/api/accounts/<account_id>/health` - Real-time health status
- `/api/accounts/export` - Export account configurations
- `/api/events` - Server-sent events for real-time updates

## Configuration

### Environment Variables (.env)
```env
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USERNAME=mcintyre@corrinbox.com
SMTP_PASSWORD=Slaypap3!!
IMAP_HOST=imap.hostinger.com
IMAP_PORT=993
ENCRYPTION_KEY=<Fernet key for credential encryption>
```

### Database Configuration
- **Path**: `email_manager.db` (SQLite)
- **Key File**: `key.txt` (Fernet encryption key, auto-generated)
- **Initialization**: Run `python populate_test_accounts.py` to set up

### Email Account Configuration
Accounts stored in SQLite `email_accounts` table with:
- Encrypted passwords using Fernet
- Provider-specific settings (Gmail, Hostinger, Outlook, Custom)
- SSL/TLS configuration (use_ssl flags)
- Connection status tracking (last_checked, last_error)
- IMAP/SMTP/POP3 support (ports and hosts configurable)

## Working Email Accounts

### Test Account Credentials (FOR TESTING ONLY)

#### Gmail Account 1 - NDayijecika
- **Email**: ndayijecika@gmail.com
- **Regular Password**: VDMcQeklCH2mom (for login to Gmail)
- **App Password**: `gbrw tagu ayhy wtry` (WITH SPACES - for IMAP/SMTP)
- **SMTP**: smtp.gmail.com:587 (STARTTLS)
- **IMAP**: imap.gmail.com:993 (SSL)
- **Status**: ✅ Verified working (133 messages in inbox)

#### Gmail Account 2 - Test Email Manager
- **Email**: test.email.manager@gmail.com
- **App Password**: (needs to be configured)
- **SMTP**: smtp.gmail.com:587 (STARTTLS)
- **IMAP**: imap.gmail.com:993 (SSL)

#### Hostinger Account
- **Email**: mcintyre@corrinbox.com
- **Password**: Slaypap3!!
- **SMTP**: smtp.hostinger.com:465 (SSL)
- **IMAP**: imap.hostinger.com:993 (SSL)
- **Username**: Use full email address

### Gmail Configuration Notes
- Requires App Password (not regular password)
- App Password format: `xxxx xxxx xxxx xxxx` (keep spaces)
- Must have 2-Factor Authentication enabled
- IMAP must be enabled in Gmail settings
- Use STARTTLS for SMTP on port 587

### Hostinger Configuration Notes
- Uses SSL for both SMTP and IMAP
- Full email address as username
- Port 465 for SMTP (SSL)
- Port 993 for IMAP (SSL)

## Template System

All templates extend `base.html` which provides:
- Bootstrap 5.3 styling
- Sidebar navigation
- User context
- Flash message handling

Key templates:
- `base.html` - Master template with sidebar navigation and modern styling
- `dashboard_unified.html` - Tabbed dashboard with account selector
- `email_queue.html` - Email queue with improved visibility and persistent counts
- `accounts_simple.html` - Account management with connection testing
- `accounts_enhanced.html` - Advanced account monitoring (optional)
- `add_account.html` - Account configuration form
- `test_dashboard.html` - Email workflow testing interface

## Threading Model

The application uses multiple threads:
- Main Flask thread (web server)
- SMTP proxy thread (email interception)
- IMAP monitor threads (one per account)
- Background cleanup thread (old email purging)

Thread management via:
- `daemon=True` for auto-cleanup on exit
- `threading.Event()` for graceful shutdown
- Connection pooling for database access

## Security Considerations

- Passwords encrypted using Fernet symmetric encryption
- Session-based authentication with Flask-Login
- Role-based access control (admin/user roles)
- SQL injection prevention via parameterized queries
- XSS protection via Jinja2 auto-escaping
- CSRF protection via Flask-WTF (when forms used)

## Common Issues & Solutions

### Gmail App Password
- Must use App Password, not regular password
- Keep spaces in App Password: `xxxx xxxx xxxx xxxx`
- Enable 2FA before creating App Password

### Database Issues
- Database path: `email_manager.db` (not `data/emails.db`)
- Use 10-second timeout: `conn.execute("PRAGMA busy_timeout = 10000")`
- Implement retry logic for concurrent access
- If tables missing, run `python populate_test_accounts.py`

### SMTP Proxy Port Conflicts
- Default port 8587 (avoid 25, 587, 465)
- Check with: `netstat -an | findstr :8587`
- Kill process if stuck: `taskkill /F /PID <pid>`
- Error "[Errno 10048]" means port already in use

### Template Not Found
- Ensure all templates extend `base.html`
- Check template paths are relative to `templates/` directory
- Use `accounts_simple.html` for basic account management

### Encryption Key Issues
- Key stored in `key.txt` (auto-generated if missing)
- Format: Base64 encoded Fernet key
- Don't include "Generated encryption key:" prefix in file

### API Connection Test Errors
- "SyntaxError: Unexpected token '<'" means HTML returned instead of JSON
- Usually indicates authentication issue or wrong endpoint
- Ensure using POST method for `/api/test-connection/<type>`

## Testing Strategy

1. **Unit Tests**: Individual function testing (pytest)
2. **Integration Tests**: Email flow testing
3. **Account Tests**: Per-provider connectivity
4. **UI Tests**: Playwright for browser automation
5. **Load Tests**: Concurrent email handling

## Dependencies

Core dependencies (requirements.txt):
- Flask 3.0.0 (web framework)
- aiosmtpd 1.4.4 (SMTP proxy)
- Flask-Login 0.6.3 (authentication)
- cryptography 41.0.7 (encryption)
- python-dotenv 1.0.0 (configuration)
- SQLAlchemy 2.0.23 (ORM, optional)

## Recent Improvements (August 2025)

### Email Queue Navigation
- **Fixed text visibility**: Changed from light gray (#6c757d) to dark (#212529)
- **Improved hover states**: Text stays readable, subtle background changes
- **Persistent count badges**: Each tab shows its count regardless of active tab
- **Working "All Emails" tab**: Properly shows all emails with total count
- **WCAG AA compliant**: All text meets accessibility contrast requirements

### Database & API Fixes
- Fixed SQL syntax errors in table creation
- Corrected database path to `email_manager.db`
- Added missing API endpoints (`/api/accounts/<id>`)
- Fixed JSON response handling for connection tests
- Added proper encryption key management

### Account Management
- Created simplified account template (`accounts_simple.html`)
- Added connection test functionality for IMAP/SMTP
- Implemented encrypted password storage with Fernet
- Added test account population script

### UI/UX Enhancements
- Modern card-based layouts with hover effects
- Gradient purple theme (#667eea to #764ba2)
- Responsive grid layouts (1-4 columns based on viewport)
- Toast notifications for user feedback
- Real-time status indicators with color coding

## Quick Reference

### First Time Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database with test accounts
python populate_test_accounts.py

# 3. Start the application
python simple_app.py

# 4. Login at http://localhost:5000
# Username: admin
# Password: admin123
```

### Common Tasks
```bash
# View email queue with counts
http://localhost:5000/emails

# Manage email accounts
http://localhost:5000/accounts

# Test email connectivity
http://localhost:5000/diagnostics

# Check application logs
cat app.log

# Kill stuck SMTP proxy
taskkill /F /FI "WINDOWTITLE eq *8587*"
```

### Testing Email Flow
1. Configure email client to use localhost:8587 as SMTP
2. Send test email - it will be intercepted
3. Review in dashboard at /emails
4. Approve/Reject/Edit as needed
5. Approved emails sent via configured relay

## Development Workflow

1. Make changes to `simple_app.py` or templates
2. No build step required (Python interpreted)
3. Restart application to apply changes
4. Test using `/test-dashboard` interface
5. Check logs in `app.log` and browser console
6. Run integration tests with test scripts