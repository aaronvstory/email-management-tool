# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Email Management Tool is a comprehensive Python Flask application for intercepting, moderating, and managing emails across multiple accounts. It provides a web dashboard for reviewing emails before they're sent, with full audit trails and modification capabilities. The application features real-time IMAP/SMTP monitoring, encrypted credential storage, and a modern responsive UI.

**Current Version:** 2.0 (September 2025)
**Status:** Production-ready with full email management suite
**Python:** 3.8+ required
**Framework:** Flask 3.0.0 with Bootstrap 5.3

## Quick Start Commands

### Starting the Application
```bash
# Professional launcher with menu (RECOMMENDED)
EmailManager.bat

# Quick launcher with auto-browser
launch.bat

# Direct Python execution
python simple_app.py

# PowerShell management
.\manage.ps1 start
```

### Access Points
- **Web Dashboard:** http://localhost:5000
- **SMTP Proxy:** localhost:8587
- **Login:** admin / admin123

### Testing & Validation
```bash
# Test all email account connections
python scripts\test_all_connections.py

# Run comprehensive validation
python archive\tests\comprehensive_test.py

# Test email workflow
python archive\tests\test_email_workflow.py

# Check database schema
python -c "import sqlite3; conn = sqlite3.connect('email_manager.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(email_messages)'); print(cursor.fetchall())"
```

## High-Level Architecture

### Core Application Structure
```
simple_app.py (1700+ lines) - Monolithic Flask application
├── Web Server (Flask)
│   ├── Authentication Layer (Flask-Login)
│   ├── Route Handlers (25+ endpoints)
│   └── Template Rendering (Jinja2)
├── SMTP Proxy Server (aiosmtpd)
│   └── EmailModerationHandler class
├── IMAP Monitoring System
│   └── Per-account monitoring threads
├── Database Layer (SQLite)
│   └── Encrypted credential storage (Fernet)
└── Background Services
    ├── Email processing threads
    └── Account monitoring threads
```

### Threading Model
- **Main Thread:** Flask web server
- **SMTP Thread:** Email interception proxy (daemon)
- **IMAP Threads:** One per active account (daemon)
- **Processing:** Async email handling

### Email Processing Pipeline
```
1. SMTP Interception (port 8587)
   ↓
2. Risk Assessment & Storage
   ↓
3. Dashboard Review (PENDING status)
   ↓
4. Manual Edit/Modification (optional)
   ↓
5. Approval/Rejection Decision
   ↓
6. SMTP Relay to Destination
   ↓
7. Audit Trail & Logging
```

## Database Schema

### Critical Tables
```sql
-- Email accounts with encrypted credentials
email_accounts (
    id INTEGER PRIMARY KEY,
    account_name TEXT,
    email_address TEXT,
    imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
    smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl,
    is_active BOOLEAN,
    last_checked, last_error,
    created_at, updated_at
)

-- Email messages with full audit trail
email_messages (
    id INTEGER PRIMARY KEY,
    message_id TEXT UNIQUE,
    sender, recipients, subject,
    body_text, body_html,
    raw_content,
    status TEXT, -- PENDING/APPROVED/REJECTED/SENT
    risk_score INTEGER,
    keywords_matched TEXT,
    account_id INTEGER,
    review_notes TEXT,
    sent_at TEXT,
    approved_by TEXT,
    reviewer_id INTEGER,
    created_at, processed_at, action_taken_at
)
```

### Database Access Pattern
```python
# CRITICAL: Always use row_factory for dictionary access
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # Enable dict-like access
cursor = conn.cursor()
# Access with: row['column_name'] not row[index]
```

## UI/UX Style Guide

### Design System
**Theme:** Modern gradient purple/pink (#667eea to #764ba2)
**Framework:** Bootstrap 5.3 with custom CSS
**Icons:** Bootstrap Icons + Font Awesome 6.5

### Color Palette
```css
:root {
    --primary-color: #4361ee;      /* Electric blue */
    --secondary-color: #3f37c9;     /* Deep purple */
    --success-color: #06ffa5;       /* Mint green */
    --danger-color: #ff006e;        /* Hot pink */
    --warning-color: #ffbe0b;       /* Golden yellow */
    --dark-bg: #0a0e27;            /* Dark navy */
    --card-bg: #1a1f3a;            /* Card background */
    --text-light: #b8bfc6;         /* Light gray text */
}
```

### Component Styling
- **Cards:** Rounded corners (border-radius: 15px), subtle shadows
- **Buttons:** Gradient backgrounds, hover effects with transform
- **Modals:** Backdrop blur, slide-in animations
- **Tables:** Striped rows, hover states, responsive scrolling
- **Badges:** Color-coded status indicators
- **Forms:** Floating labels, validation feedback

### Layout Principles
- **Sidebar Navigation:** Fixed left, 250px width, dark theme
- **Content Area:** Fluid width, 20px padding, max-width 1400px
- **Responsive Breakpoints:** sm:640px, md:768px, lg:1024px, xl:1280px
- **Card Grid:** 4 columns on desktop, 2 on tablet, 1 on mobile

## Feature Implementation Details

### Email Interception
```python
# SMTP Proxy Handler (Port 8587)
class EmailModerationHandler:
    async def handle_DATA(self, server, session, envelope):
        # 1. Parse email
        # 2. Calculate risk score
        # 3. Store in database as PENDING
        # 4. Return '250 Message accepted for delivery'
```

### Email Modification
```javascript
// Frontend: Edit modal with live preview
function editEmail(emailId) {
    // Fetch email data
    // Populate modal fields
    // Enable rich text editing
    // Save changes via API
}
```

### Multi-Account Management
- Gmail: App passwords required (with spaces)
- Hostinger: Direct SMTP/IMAP credentials
- Outlook: App passwords for 2FA accounts
- Each account runs independent IMAP monitor thread

### Security Implementation
- **Passwords:** Encrypted with Fernet symmetric encryption
- **Sessions:** Flask-Login with secure cookies
- **Authentication:** Bcrypt password hashing
- **Audit Trail:** All modifications logged with timestamp/user

## API Endpoints

### Core Routes
```python
GET  /                      # Login page
GET  /dashboard            # Main dashboard with tabs
GET  /emails               # Email queue (status filter)
GET  /inbox                # Inbox viewer
GET  /compose              # Email composer
POST /compose              # Send new email
GET  /accounts             # Account management
POST /accounts/add         # Add new account
GET  /diagnostics          # Connection testing
```

### Email Management API
```python
GET  /email/<id>/edit      # Get email for editing
POST /email/<id>/edit      # Save email modifications
POST /email/<id>/action    # Approve/reject email
GET  /email/<id>           # View email details
```

### RESTful API
```python
GET  /api/stats                           # Dashboard statistics
POST /api/test-connection/<type>          # Test IMAP/SMTP
GET  /api/diagnostics/<account_id>        # Account diagnostics
GET  /api/accounts/<account_id>/health    # Health check
GET  /api/metrics                         # Performance metrics
```

## JavaScript Functions

### Email Queue Management
```javascript
// Edit email with audit trail
function editEmail(emailId) { /* Opens modal, loads content */ }
function saveEmailChanges() { /* Saves via API with review notes */ }

// Status filtering
function filterByStatus(status) { /* Reloads with query param */ }
```

### Inbox Features
```javascript
// Account filtering
function filterByAccount(accountId) { /* Filter emails by account */ }

// Auto-refresh (30 seconds)
setInterval(function() {
    if (!document.hidden) location.reload();
}, 30000);
```

### Compose Interface
```javascript
// Character counting
function updateCharCount(fieldId, counterId, maxLength) { }

// Draft auto-save to localStorage
setInterval(saveDraft, 10000);

// Formatting toolbar
function insertText(text) { /* Rich text insertion */ }
```

## Configuration & Settings

### Environment Variables (.env)
```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///email_manager.db
SMTP_PROXY_PORT=8587
WEB_PORT=5000
DEBUG=True
```

### Gmail Configuration
1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use WITH spaces: `xxxx xxxx xxxx xxxx`
4. Enable IMAP in Gmail settings
5. SMTP: smtp.gmail.com:587 (STARTTLS)
6. IMAP: imap.gmail.com:993 (SSL)

### Active Test Accounts
```
1. Gmail Test: test.email.manager@gmail.com
2. Hostinger: mcintyre@corrinbox.com
3. Gmail NDayijecika: ndayijecika@gmail.com
```

## Project Structure

```
Email-Management-Tool/
├── simple_app.py              # Main Flask application
├── email_manager.db           # SQLite database
├── key.txt                    # Fernet encryption key
├── templates/                 # Jinja2 templates
│   ├── base.html             # Master template
│   ├── login.html            # Login page
│   ├── dashboard_unified.html # Main dashboard
│   ├── email_queue.html      # Email management
│   ├── inbox.html            # Inbox viewer
│   ├── compose.html          # Email composer
│   └── accounts_simple.html  # Account management
├── static/                    # CSS/JS assets
├── archive/                   # Archived files
│   ├── tests/                # Test scripts
│   └── test-results/         # JSON results
├── scripts/                   # Utility scripts
├── config/                    # Configuration files
└── docs/                      # Documentation
```

## Development Workflow

### Adding New Features
1. Update database schema if needed
2. Add route handler in simple_app.py
3. Create/update template in templates/
4. Add JavaScript functions if interactive
5. Update CLAUDE.md documentation

### Database Migrations
```python
# Add new column
cursor.execute('ALTER TABLE email_messages ADD COLUMN new_field TEXT')

# Always check for column existence first
cursor.execute('PRAGMA table_info(email_messages)')
columns = [col[1] for col in cursor.fetchall()]
if 'new_field' not in columns:
    cursor.execute('ALTER TABLE email_messages ADD COLUMN new_field TEXT')
```

### Error Handling Pattern
```python
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Database operations
except sqlite3.Error as e:
    app.logger.error(f"Database error: {e}")
    return jsonify({'error': 'Database error'}), 500
finally:
    conn.close()
```

## Testing Strategy

### Unit Testing
```python
# Test individual functions
python -m pytest tests/unit/

# Test specific feature
python tests/unit/test_email_interception.py
```

### Integration Testing
```python
# Full workflow test
python archive/tests/comprehensive_test.py

# Connection testing
python scripts/test_all_connections.py
```

### Manual Testing Checklist
- [ ] Email interception via SMTP proxy
- [ ] Email modification before approval
- [ ] Multi-account switching
- [ ] Inbox auto-refresh
- [ ] Compose and send
- [ ] Search and filter
- [ ] Audit trail logging

## Performance Optimization

### Database
- Use indexes on frequently queried columns
- Batch operations where possible
- Connection pooling for concurrent access
- 10-second timeout for locks

### Threading
- Daemon threads for clean shutdown
- Thread-safe queue for email processing
- Async SMTP handling
- Non-blocking IMAP monitoring

### Frontend
- Debounced auto-save (10 seconds)
- Virtual scrolling for large lists
- Lazy loading for images
- LocalStorage for draft persistence

## Security Considerations

### Credential Storage
- All passwords encrypted with Fernet
- Key file never committed to git
- Separate encryption per account

### Session Management
- Flask-Login for authentication
- Secure session cookies
- Automatic timeout after inactivity
- CSRF protection on forms

### Audit Trail
- All modifications logged
- Username and timestamp tracked
- Review notes mandatory
- IP address logging (optional)

## Troubleshooting

### Common Issues

#### "getaddrinfo() argument 1 must be string or None"
```python
# Fix: Always set row_factory
conn.row_factory = sqlite3.Row
```

#### Gmail Authentication Failed
- Use App Password, not regular password
- Keep spaces in App Password
- Check 2FA is enabled

#### Port Already in Use
```bash
# Find process
netstat -an | findstr :8587
# Kill specific PID
taskkill /F /PID <pid>
```

#### Database Schema Mismatch
```python
# Check and add missing columns
python scripts/migrate_database.py
```

## Future Enhancements Roadmap

1. **WebSocket Support** - Real-time updates without refresh
2. **Advanced Rules Engine** - Automated filtering/routing
3. **Email Templates** - Customizable response templates
4. **API Authentication** - OAuth2/JWT for external access
5. **Attachment Handling** - File upload/download support
6. **Scheduling System** - Delayed send functionality
7. **Analytics Dashboard** - Email statistics and trends
8. **Mobile App** - React Native companion app
9. **Backup/Restore** - Automated database backups
10. **Multi-language Support** - i18n implementation

---
*Last Updated: September 14, 2025*
*Version: 2.0 - Full Production Release*