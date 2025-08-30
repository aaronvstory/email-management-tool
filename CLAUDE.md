# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status & Structure

**CURRENT STATE**: Production-ready Windows-native application with **NO DOCKER** dependencies. The application runs directly on Windows using Python virtual environments and can be installed as a Windows service for production deployment.

### Implementation Approach - NO DOCKER
- **NO DOCKER REQUIRED**: Application runs natively on Windows - no containers
- **Virtual Environment**: Python venv for dependency isolation
- **Windows Service**: Optional installation as Windows service via PowerShell
- **Batch Scripts**: Simple setup.bat and start.bat for easy management
- **PowerShell Management**: Advanced manage.ps1 for production operations

## Project Overview

Email Management Tool is a **Windows-native** Python email moderation system that intercepts, holds, and allows review of emails before sending. It uses an SMTP proxy server to capture outgoing emails and a Flask web dashboard for moderation. **No Docker, no containers - pure Windows Python application**.

## Development Commands - Windows Native

### Initial Setup (Windows)

```batch
# One-time setup - creates venv and installs dependencies
setup.bat
```

### Starting the Application

```batch
# Start application with virtual environment
start.bat

# Or use PowerShell for more control
powershell .\manage.ps1 start
```

### Managing the Application (PowerShell)

```powershell
# View status
.\manage.ps1 status

# Stop application
.\manage.ps1 stop

# Restart application
.\manage.ps1 restart

# Create backup
.\manage.ps1 backup

# View logs
.\manage.ps1 logs

# Install as Windows Service (requires Admin)
.\manage.ps1 install

# Uninstall Windows Service
.\manage.ps1 uninstall
```

### Testing and Validation

```batch
# Activate virtual environment first
venv\Scripts\activate

# Test SMTP proxy connection
telnet localhost 8587

# Check if services are running (Windows)
netstat -an | findstr 8587
netstat -an | findstr 5000

# View logs (Windows)
type logs\email_moderation.log
```

## High-Level Architecture

### Core Components

1. **SMTP Proxy Server (`simple_app.py`)**: Intercepts emails on port 8587, applies moderation rules, and queues messages for review
2. **Web Dashboard (Flask)**: Web interface on port 5000 for email review, editing, and approval
3. **Email Delivery Service**: Handles sending approved emails through configured SMTP relay
4. **SQLite Database**: Stores emails, users, rules, and audit logs - no external database required

### Windows-Specific Implementation

- **Threading Model**: Main thread for Flask, background thread for SMTP proxy
- **File Paths**: Windows path handling with proper separators
- **Service Support**: Can run as Windows service via NSSM or SC.exe
- **Virtual Environment**: Standard Python venv in `venv\` directory
- **Logs**: Automatic rotation in `logs\` directory

### Configuration Management

Configuration in `config\config.ini` (Windows path format):
- `SMTP_PROXY`: Proxy server settings (host, port, message size limits)
- `SMTP_RELAY`: External SMTP server for sending approved emails
- `WEB_INTERFACE`: Flask app configuration
- `DATABASE`: SQLite database path (data\email_moderation.db)
- `SECURITY`: Session timeout, login attempts, lockout settings

## Key Development Patterns - Windows Focus

### File Organization (Windows Structure)

```
Email Management Tool\
├── initial\                 # Original prototype files (reference)
├── app\                     # Application modules
│   ├── models\             # SQLAlchemy models
│   ├── routes\             # Flask routes
│   └── services\           # Business logic
├── config\                  # Configuration files
│   └── config.ini          # Main config (Windows format)
├── data\                    # SQLite database
├── logs\                    # Application logs
├── templates\               # HTML templates
├── static\                  # CSS, JS, images
├── venv\                    # Python virtual environment
├── backups\                 # Database backups
├── setup.bat                # Windows setup script
├── start.bat                # Application launcher
├── manage.ps1               # PowerShell management
├── simple_app.py            # Main application
└── requirements.txt         # Python dependencies
```

### Windows Path Handling

```python
import os
from pathlib import Path

# Use Path for cross-platform compatibility
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config" / "config.ini"
DB_PATH = BASE_DIR / "data" / "email_moderation.db"

# Or use os.path.join for Windows
config_path = os.path.join(os.getcwd(), "config", "config.ini")
```

### Database Operations (SQLite - No External DB)

```python
# SQLite connection - works perfectly on Windows
import sqlite3
conn = sqlite3.connect('data\\email_moderation.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
# ... operations ...
conn.commit()
conn.close()
```

## Common Development Tasks

### Running in Development Mode

1. Activate virtual environment: `venv\Scripts\activate`
2. Set debug mode in config\config.ini
3. Run: `python simple_app.py`

### Adding New Features

1. Always work within virtual environment
2. Install new packages: `pip install package_name`
3. Update requirements: `pip freeze > requirements.txt`
4. Test with: `start.bat`

### Creating Windows Service

```powershell
# Run PowerShell as Administrator
.\manage.ps1 install

# Service will auto-start on Windows boot
# Access dashboard at http://localhost:5000
```

### Backup and Recovery

```powershell
# Create backup
.\manage.ps1 backup

# Restore from backup
.\manage.ps1 restore
```

## Security Considerations - Windows Environment

- **Password Storage**: Bcrypt hashing for all passwords
- **Session Management**: Flask-Login with secure cookies
- **Windows Firewall**: Configure rules for ports 5000 and 8587
- **Service Account**: Run service with limited privileges
- **File Permissions**: Restrict access to config and data directories

## Testing Email Flow - Windows

1. Configure Outlook/Thunderbird to use localhost:8587 as SMTP
2. Send test email with keywords (invoice, urgent, etc.)
3. Open browser to http://127.0.0.1:5000
4. Login with admin/admin123
5. Review and approve/reject emails

## Debugging on Windows

- View logs: `type logs\email_moderation.log`
- Check services: `powershell .\manage.ps1 status`
- Test ports: `netstat -an | findstr "5000 8587"`
- Database issues: Check data\ directory permissions
- Python issues: Ensure venv is activated

## Important Notes - NO DOCKER

- **This application does NOT use Docker**
- **Runs natively on Windows with Python**
- **No containers, no virtualization overhead**
- **Direct Windows service integration**
- **Simple batch files for management**
- **PowerShell for advanced operations**

## Performance on Windows

- Handles 1000+ emails/hour on modest hardware
- SQLite supports databases up to 100GB
- Memory usage: 50-100MB typical
- CPU usage: <5% during normal operation
- Startup time: <5 seconds

## Windows-Specific Features

1. **Windows Service Mode**: Runs in background, starts with Windows
2. **PowerShell Management**: Full control via manage.ps1
3. **Event Viewer Integration**: Logs to Windows Event Log (when service)
4. **Windows Authentication**: Can integrate with Active Directory
5. **Network Drive Support**: Can store data on network shares
6. **Batch File Automation**: Simple .bat files for all operations