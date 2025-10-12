# 🚀 Email Management Tool - Quick Start Guide

Get the Email Management Tool running in under 5 minutes!

## ⚡ Prerequisites

- **Python 3.9+** installed
- **Windows 10/11** (or Linux/Mac with minor adjustments)
- **100MB free space**

## 📦 Step 1: Install Dependencies

```bash
# Install required packages
pip install flask flask-login flask-wtf python-dotenv imapclient sqlalchemy cryptography
```

## 🔧 Step 2: Configure Environment (Optional)

The app works out-of-the-box with defaults, but you can customize:

```bash
# Copy the example config
copy .env.example .env

# Edit .env to customize (optional)
# - Change ports, enable/disable features
# - Add email account credentials for testing
```

## ▶️ Step 3: Start the Application

```bash
# Simple startup - one command!
python start.py
```

That's it! The app will:
- ✅ Check dependencies
- ✅ Initialize database (if needed)
- ✅ Start web dashboard on http://localhost:5000
- ✅ Start SMTP proxy on localhost:8587

## 🌐 Step 4: Access the Dashboard

1. **Open browser**: http://localhost:5000
2. **Login with**:
   - Username: `admin`
   - Password: `admin123`

## 📧 Step 5: Test Email Interception (Optional)

Configure your email client to use:
- **SMTP Server**: `localhost`
- **Port**: `8587`
- **Security**: None
- **Authentication**: None required

Send a test email - it will appear in the dashboard for review!

## 🛠️ Management Commands

```bash
# Start the app
python start.py

# Run tests
python -m pytest tests/ -v

# Import accounts from CSV
python scripts/bulk_import_accounts.py accounts.csv --auto-detect

# View help
python start.py --help
```

## 🔧 Troubleshooting

### App won't start?
```bash
# Check Python version
python --version

# Check dependencies
python -c "import flask, flask_wtf; print('OK')"
```

### Can't access dashboard?
- Check if port 5000 is available
- Try http://127.0.0.1:5000
- Check firewall settings

### Emails not intercepting?
- Verify email client SMTP settings
- Check app logs for errors
- Ensure SMTP proxy started (should show in startup output)

## 📁 Key Files

- `start.py` - Main startup script
- `.env` - Configuration (optional)
- `email_manager.db` - SQLite database
- `scripts/` - Utility scripts
- `tests/` - Test suite

## 🎯 What's Working

✅ **Database**: SQLite with encryption
✅ **Web UI**: Modern dashboard with dark theme
✅ **Authentication**: Secure login system
✅ **Email interception**: IMAP watchers + SMTP proxy
✅ **API**: RESTful endpoints for integration
✅ **Security**: CSRF protection, rate limiting
✅ **Tests**: Comprehensive test suite

## 📞 Need Help?

- Check the logs: `app.log`
- Run diagnostics: Visit `/diagnostics` in the dashboard
- View API docs: `/api/docs` (if enabled)

---

**Ready to intercept emails?** Run `python start.py` and start exploring! 🎉