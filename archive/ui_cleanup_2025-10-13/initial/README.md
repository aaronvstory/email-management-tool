# Email Moderation System - Setup Guide

## Quick Start for Windows

### Prerequisites
1. **Python 3.8+** - Download from https://python.org
2. **Git** (optional) - For version control

### Installation Steps

1. **Extract or clone the email moderation system files**
   ```
   # If using git:
   git clone <repository_url>
   cd email_moderation_system

   # Or extract ZIP to a folder and navigate to it
   cd email_moderation_system
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**
   - Edit `config/config.ini`
   - Update IMAP and SMTP settings with your email server details
   - For Gmail, use:
     - IMAP: imap.gmail.com:993 (SSL)
     - SMTP: smtp.gmail.com:587 (TLS)

4. **Run the system**
   ```bash
   python main.py
   ```

### Configuration Example (Gmail)

Edit `config/config.ini`:

```ini
[SMTP_PROXY]
host = 0.0.0.0
port = 8587
max_message_size = 33554432

[IMAP_SETTINGS]
imap_server = imap.gmail.com
imap_port = 993
use_ssl = true

[SMTP_RELAY]
relay_host = smtp.gmail.com
relay_port = 587
use_tls = true

[WEB_INTERFACE]
host = 127.0.0.1
port = 5000
debug = true
secret_key = change-this-secret-key-in-production
```

### Email Client Configuration

Configure your email client to use the moderation proxy:

**Outgoing SMTP Settings:**
- Server: 127.0.0.1 (or your server IP)
- Port: 8587
- Security: None (for local testing)
- Authentication: Use your normal email credentials

**For Gmail Users:**
1. Enable 2-factor authentication
2. Create an App Password: https://myaccount.google.com/apppasswords
3. Use the app password instead of your regular password

### Testing the System

1. **Start the system**
   ```bash
   python main.py
   ```

2. **Access the web dashboard**
   - Open browser to http://127.0.0.1:5000
   - You should see the Email Moderation Dashboard

3. **Send a test email**
   - Configure your email client with proxy settings above
   - Send an email containing keywords like "urgent" or "invoice"
   - Check the web dashboard - email should appear in pending queue

4. **Moderate the email**
   - Click on the email in the queue
   - Click "Edit Message" to modify content
   - Add your name as reviewer
   - Click "Save & Approve"

### Directory Structure
```
email_moderation_system/
├── main.py                 # Main application runner
├── requirements.txt        # Python dependencies
├── config/
│   └── config.ini         # Configuration file
├── app/
│   ├── models.py          # Database models
│   ├── smtp_proxy.py      # SMTP interception server
│   ├── web_app.py         # Flask web application
│   └── email_delivery.py  # Email delivery service
├── templates/             # HTML templates
│   ├── dashboard.html
│   ├── queue.html
│   ├── message_detail.html
│   └── message_edit.html
├── static/               # CSS/JS files (empty for now)
├── data/                 # SQLite database storage
└── logs/                 # Application logs
```

### Default Moderation Rules

The system comes with these pre-configured rules:
- **Invoice Detection**: Holds emails containing "invoice", "billing", "payment", "receipt"
- **Urgent Messages**: Holds emails with "urgent", "asap", "immediate", "emergency"
- **Attachment Detection**: Holds emails with PDF, DOC, XLS attachments
- **External Recipients**: Holds emails sent to external domains

### Troubleshooting

**Port already in use:**
- Change the port in config/config.ini
- Use `netstat -an | findstr 8587` to check if port is occupied

**Email client won't connect:**
- Disable firewall temporarily to test
- Ensure SMTP proxy is running (check logs)
- Verify port and host settings

**No emails appearing in queue:**
- Check that moderation rules are triggering
- Verify database is created in `data/` folder
- Check application logs in `logs/` folder

**Can't approve/send emails:**
- Configure valid SMTP relay credentials in config
- Check internet connection for relay server
- Verify recipient email addresses are valid

### Security Notes

⚠️ **This is a development/testing version:**
- No TLS encryption on SMTP proxy (add for production)
- Passwords stored in plain text (encrypt for production)
- No authentication on web interface (add for production)
- SQLite database (use PostgreSQL for production)

### Next Steps

1. Configure real SMTP/IMAP credentials
2. Test with your actual email account
3. Add more sophisticated moderation rules
4. Customize the web interface styling
5. Deploy to a server for organizational use

For production deployment, additional security hardening is required.
