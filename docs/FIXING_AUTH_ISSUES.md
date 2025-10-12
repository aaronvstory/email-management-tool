# Quick Guide: Fixing IMAP Authentication Issues

## TL;DR

```bash
# 1. Diagnose the problem
python scripts/diagnose_imap.py

# 2. Fix credentials (see provider-specific guides below)

# 3. Re-activate account
python -c "import sqlite3; conn=sqlite3.connect('email_manager.db'); conn.execute('UPDATE email_accounts SET is_active=1, last_error=NULL WHERE id=1'); conn.commit(); print('Account re-activated')"

# 4. Restart application
.\manage.ps1 start
```

## Provider-Specific Guides

### Gmail

**Problem**: `AUTHENTICATIONFAILED` error

**Root Cause**: Gmail requires App Passwords when 2FA is enabled

**Solution**:
1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or Other)
   - Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
3. Update account in Email Management Tool:
   - Go to http://localhost:5000/accounts
   - Edit the Gmail account
   - Paste App Password in IMAP Password field (with or without spaces)
   - Save
4. Re-activate if circuit breaker tripped:
   ```sql
   UPDATE email_accounts SET is_active=1, last_error=NULL WHERE id=<gmail_account_id>;
   ```

**IMAP Settings**:
- IMAP Host: `imap.gmail.com`
- IMAP Port: `993`
- Use SSL: `Yes` (checked)
- Username: Full email address (e.g., `user@gmail.com`)

### Outlook / Hotmail / Live

**Problem**: `AUTHENTICATIONFAILED` error

**Root Cause**: Outlook requires App Passwords when 2FA is enabled

**Solution**:
1. Enable 2-Step Verification: https://account.live.com/proofs/manage
2. Generate App Password: https://account.live.com/proofs/AppPassword
   - Give it a name (e.g., "Email Management Tool")
   - Copy the generated password
3. Update account in Email Management Tool:
   - Go to http://localhost:5000/accounts
   - Edit the Outlook account
   - Paste App Password in IMAP Password field
   - Save
4. Re-activate if needed (see SQL command above)

**IMAP Settings**:
- IMAP Host: `outlook.office365.com` or `imap-mail.outlook.com`
- IMAP Port: `993`
- Use SSL: `Yes` (checked)
- Username: Full email address (e.g., `user@outlook.com`)

### Hostinger

**Problem**: `AUTHENTICATIONFAILED` error or wrong settings

**Root Cause**: Incorrect IMAP settings or regular password not working

**Solution**:
1. Verify IMAP is enabled in Hostinger control panel
2. Use regular password (NOT App Password)
3. Update account with correct settings:
   - IMAP Host: `imap.hostinger.com`
   - IMAP Port: `993`
   - Use SSL: `Yes` (checked)
   - Username: Full email address (e.g., `user@domain.com`)
   - Password: Regular account password
4. If still failing, check:
   - Email account is active and not suspended
   - Password was entered correctly
   - No special characters causing issues

**IMAP Settings**:
- IMAP Host: `imap.hostinger.com`
- IMAP Port: `993`
- Use SSL: `Yes` (checked)
- Username: Full email address

### Other Providers

**Common IMAP Settings**:

| Provider | IMAP Host | Port | SSL | Notes |
|----------|-----------|------|-----|-------|
| Yahoo | imap.mail.yahoo.com | 993 | Yes | Requires App Password if 2FA enabled |
| ProtonMail | 127.0.0.1 | 1143 | No | Requires ProtonMail Bridge |
| FastMail | imap.fastmail.com | 993 | Yes | Regular password or App Password |
| iCloud | imap.mail.me.com | 993 | Yes | Requires App-Specific Password |
| Zoho | imap.zoho.com | 993 | Yes | Regular password |

## Diagnostic Workflow

### Step 1: Identify the Issue

Run diagnostic script:
```bash
python scripts/diagnose_imap.py
```

Look for error patterns:
- `❌ AUTHENTICATION FAILURE` → Wrong credentials or App Password needed
- `❌ SSL/TLS ERROR` → Wrong port or SSL setting
- `❌ CONNECTION TIMEOUT` → Firewall or network issue
- `❌ CONNECTION REFUSED` → Wrong host or IMAP not enabled
- `⚠️  Account is marked as inactive` → Circuit breaker tripped

### Step 2: Check Account Status

Query database:
```bash
python -c "import sqlite3; conn=sqlite3.connect('email_manager.db'); cur=conn.cursor(); rows=cur.execute('SELECT id, account_name, is_active, last_error FROM email_accounts ORDER BY id').fetchall(); print('ID | Active | Error'); print('-'*60); [print(f'{r[0]:2} | {bool(r[2]):5} | {(r[3] or \"\")[:50]}') for r in rows]"
```

### Step 3: Fix Credentials

Based on provider, update credentials:
1. Via Web UI: http://localhost:5000/accounts (edit account)
2. Via Database:
   ```sql
   -- Check current settings
   SELECT id, account_name, imap_host, imap_port, imap_username, is_active
   FROM email_accounts
   WHERE id=<account_id>;

   -- Update credentials (password will be encrypted automatically via UI)
   -- Use web UI to update passwords securely
   ```

### Step 4: Re-activate Account

If circuit breaker tripped (is_active=0):
```sql
UPDATE email_accounts
SET is_active=1, last_error=NULL
WHERE id=<account_id>;
```

Or via Python:
```bash
python -c "import sqlite3; conn=sqlite3.connect('email_manager.db'); conn.execute('UPDATE email_accounts SET is_active=1, last_error=NULL WHERE id=<account_id>'); conn.commit(); print('Re-activated')"
```

### Step 5: Verify Fix

```bash
# Test specific account
python scripts/diagnose_imap.py <account_id>

# Test all accounts
python scripts/diagnose_imap.py
```

Expected output:
```
✅ CONNECTION SUCCESSFUL!
✅ ALL TESTS PASSED - Account is properly configured
```

## Common Errors and Fixes

### Error: "Password decryption returned None/empty"

**Cause**: Encryption key mismatch or corrupted password in database

**Fix**:
1. Re-enter password via web UI (http://localhost:5000/accounts)
2. If key.txt was deleted/corrupted, all passwords need re-entry
3. Check `key.txt` exists and is readable

### Error: "Missing credentials for account"

**Cause**: Username or password field is empty in database

**Fix**:
1. Edit account via web UI
2. Enter all required fields
3. Save and test

### Error: "Client tried to access nonexistent namespace"

**Cause**: Wrong folder name format for provider

**Fix**: Already handled automatically by code - tries multiple folder variants:
- `Quarantine`
- `INBOX/Quarantine`
- `INBOX.Quarantine`

If you see this error persist, check provider's folder naming convention.

### Error: "All COPY attempts failed"

**Cause**: Quarantine folder cannot be created or accessed

**Fix**:
1. Manually create `Quarantine` folder in email client
2. Or use `INBOX.Quarantine` format (auto-created by code)
3. Check folder permissions in email account

## Prevention

### Before Adding Account

1. Test credentials manually:
   - Use email client (Thunderbird, Outlook) to verify IMAP works
   - Confirm folder access
2. Generate App Passwords in advance (Gmail/Outlook)
3. Have IMAP host/port ready for provider

### After Adding Account

1. Run diagnostic immediately:
   ```bash
   python scripts/diagnose_imap.py <new_account_id>
   ```
2. Monitor logs for first few minutes:
   ```bash
   tail -f app.log | grep "account <new_account_id>"
   ```
3. Check heartbeat status:
   ```sql
   SELECT worker_id, last_heartbeat, status, error_count
   FROM worker_heartbeats
   WHERE worker_id LIKE '%<account_id>%';
   ```

## Emergency Reset

If all accounts are failing and circuit breaker has disabled them:

```bash
# 1. Stop application
.\manage.ps1 stop

# 2. Reset all accounts
python -c "import sqlite3; conn=sqlite3.connect('email_manager.db'); conn.execute('UPDATE email_accounts SET is_active=1, last_error=NULL'); conn.execute('DELETE FROM worker_heartbeats'); conn.commit(); print('All accounts reset')"

# 3. Fix credentials via web UI
# Go to http://localhost:5000/accounts and update passwords

# 4. Test each account
python scripts/diagnose_imap.py

# 5. Restart application
.\manage.ps1 start
```

## Monitoring

### Check IMAP Watcher Status

```bash
# View recent errors
tail -n 100 app.log | grep "ERROR.*IMAP"

# Check heartbeats
python -c "import sqlite3; conn=sqlite3.connect('email_manager.db'); rows=conn.execute('SELECT worker_id, last_heartbeat, status, error_count FROM worker_heartbeats ORDER BY last_heartbeat DESC').fetchall(); print('Worker | Last Heartbeat | Status | Errors'); print('-'*80); [print(f'{r[0]:20} | {r[1]:19} | {r[2]:10} | {r[3]}') for r in rows]"
```

### Watch Live Logs

```bash
# Windows PowerShell
Get-Content app.log -Wait -Tail 50

# Git Bash / WSL
tail -f app.log
```

### Key Metrics

- **Last Heartbeat**: Should update every 30 seconds when active
- **Status**: Should be "active" for running watchers
- **Error Count**: Should be 0 for healthy accounts
- **Last Error**: Should be NULL for healthy accounts

## Support

If issues persist after following this guide:

1. Run diagnostic and save output:
   ```bash
   python scripts/diagnose_imap.py > diagnostic_output.txt 2>&1
   ```

2. Check application logs:
   ```bash
   tail -n 500 app.log > last_500_lines.txt
   ```

3. Export account settings (passwords will be encrypted):
   ```bash
   python -c "import sqlite3, json; conn=sqlite3.connect('email_manager.db'); rows=conn.execute('SELECT id, account_name, imap_host, imap_port, imap_use_ssl, is_active, last_error FROM email_accounts').fetchall(); print(json.dumps([dict(zip(['id','name','host','port','ssl','active','error'], r)) for r in rows], indent=2))" > account_settings.json
   ```

4. Review documentation:
   - `docs/IMAP_FIXES_2025_10_12.md` - Detailed fix documentation
   - `docs/INTERCEPTION_IMPLEMENTATION.md` - Architecture overview
   - `README.md` - General setup and features
