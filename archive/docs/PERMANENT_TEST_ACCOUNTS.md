# Permanent Test Accounts Configuration

**Last Updated**: September 30, 2025
**Status**: ✅ FULLY OPERATIONAL
**Both accounts tested and configured successfully**

## 🔑 Account Credentials

### Account 1: Gmail - NDayijecika (Primary)
- **Email**: `ndayijecika@gmail.com`
- **Password**: `bjormgplhgwkgpad` (Gmail App Password)
- **Status**: ✅ FULLY OPERATIONAL (Tested 2025-09-30 09:47)

**IMAP Settings**:
- Host: `imap.gmail.com`
- Port: `993`
- SSL: `Yes`
- Username: `ndayijecika@gmail.com`

**SMTP Settings**:
- Host: `smtp.gmail.com`
- Port: `587`
- SSL: `No (STARTTLS)`
- Username: `ndayijecika@gmail.com`

### Account 2: Hostinger - Corrinbox (Secondary)
- **Email**: `mcintyre@corrinbox.com`
- **Password**: `25Horses807$`
- **Status**: ✅ FULLY OPERATIONAL (Tested 2025-09-30 09:47)

**IMAP Settings**:
- Host: `imap.hostinger.com`
- Port: `993`
- SSL: `Yes`
- Username: `mcintyre@corrinbox.com`

**SMTP Settings**:
- Host: `smtp.hostinger.com`
- Port: `465`
- SSL: `Yes (Direct)`
- Username: `mcintyre@corrinbox.com`

## 🎯 Quick Setup Commands

### Test Connections (No DB Required)
```bash
python scripts/test_permanent_accounts.py
```
This tests both accounts' IMAP/SMTP connectivity without modifying the database.

### Add to Database
```bash
python scripts/setup_test_accounts.py
```
This adds or updates both accounts in the email_manager.db with encrypted credentials.

### Verify Configuration
```bash
python scripts/verify_accounts.py
```
Shows current database configuration for both accounts.

## 🔧 Smart Detection Implementation

### Auto-Detection Logic
The application now includes `detect_email_settings(email_address)` function that automatically determines correct server settings based on email domain:

**Gmail Detection**:
- Domain: `gmail.com`
- SMTP: `smtp.gmail.com:587` (STARTTLS)
- IMAP: `imap.gmail.com:993` (SSL)

**Hostinger Detection**:
- Domain: `corrinbox.com`
- SMTP: `smtp.hostinger.com:465` (Direct SSL)
- IMAP: `imap.hostinger.com:993` (SSL)

### API Endpoint
```http
POST /api/detect-email-settings
Content-Type: application/json

{"email": "user@example.com"}
```

Returns auto-detected SMTP/IMAP settings for the domain.

## 📋 Configuration Rules

### Port-Based SSL Detection
- **Port 587**: Always use STARTTLS (`smtp_use_ssl=0`)
- **Port 465**: Always use Direct SSL (`smtp_use_ssl=1`)
- **Port 993**: Always use SSL for IMAP

### Username Convention
- Both accounts use **email address as username**
- No separate username field needed

### Password Format
- **Gmail**: App Password (no spaces in storage)
- **Hostinger**: Regular password with special characters

## ✅ Verification Checklist

Run this checklist after any changes:

- [ ] Test IMAP connection: `python scripts/test_permanent_accounts.py`
- [ ] Verify accounts in DB: `python scripts/setup_test_accounts.py`
- [ ] Check app running: `http://localhost:5000`
- [ ] Login successful: `admin` / `admin123`
- [ ] Accounts visible in UI: Navigate to `/accounts`
- [ ] IMAP monitoring active: Check dashboard for status
- [ ] Test email send: Use `/compose` page
- [ ] Test email receive: Send to test accounts

## 🐛 Troubleshooting

### Connection Failed
1. Run test script: `python scripts/test_permanent_accounts.py`
2. Check credentials in CLAUDE.md match
3. Verify firewall not blocking ports 587, 465, 993
4. For Gmail: Ensure 2FA enabled and App Password used

### Database Issues
1. Stop the app: `taskkill /F /IM python.exe`
2. Re-run setup: `python scripts/setup_test_accounts.py`
3. Restart app: `python simple_app.py`

### IMAP Not Monitoring
1. Check accounts are `is_active=1`
2. Verify IMAP threads started (check console logs)
3. Restart app to reinitialize threads

## 🔒 Security Notes

- Credentials stored encrypted with Fernet
- Encryption key in `key.txt` (keep secure)
- Never commit plain passwords to git
- These test accounts are documented for development only
- Change passwords regularly
- Use App Passwords for Gmail (not main password)

## 📚 Related Files

- **CLAUDE.md**: Main project documentation with account reference
- **simple_app.py**: Smart detection implementation (lines 97-160)
- **scripts/test_permanent_accounts.py**: Connection testing
- **scripts/setup_test_accounts.py**: Database setup
- **scripts/verify_accounts.py**: Configuration verification

## 🎉 Success Criteria

✅ Both accounts tested successfully
✅ Smart detection implemented
✅ Accounts added to database
✅ Encryption working
✅ IMAP/SMTP servers correct
✅ API endpoint functional
✅ Documentation complete

**RESULT**: System is fully operational with permanent test accounts configured.
