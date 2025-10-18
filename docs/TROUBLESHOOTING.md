# Troubleshooting Documentation

## Common Issues

### Gmail Authentication Failed
**Symptom**: "Authentication failed" when testing Gmail account

**Solutions**:
1. Use App Password (WITH spaces): `xxxx xxxx xxxx xxxx`
2. Verify 2FA is enabled on Gmail account
3. Ensure IMAP is enabled in Gmail settings
4. Check that App Password was generated (not regular password)
5. Username should be full email address

**Test**:
```bash
python scripts/test_permanent_accounts.py
```

### Port Already in Use
**Symptom**: "Address already in use" when starting application

**Solution**:
```bash
# Find process using port 8587
netstat -an | findstr :8587

# Kill the process
taskkill /F /PID <pid>

# Or use cleanup script
python cleanup_and_start.py
```

### Database Schema Mismatch
**Symptom**: SQLite column errors or missing fields

**Solution**:
```bash
# Run migration scripts
python scripts/migrations/20251001_add_interception_indices.py

# Verify schema
python -c "import sqlite3; conn = sqlite3.connect('email_manager.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(email_messages)'); print(cursor.fetchall())"
```

### IMAP Authentication Failures (All Accounts)
**Symptoms**:
- All IMAP watchers fail to connect
- "Authentication failed" in logs for multiple accounts

**Diagnosis**:
```bash
# Check DB-stored credentials
python scripts/verify_accounts.py

# Test connections outside watchers
python scripts/test_permanent_accounts.py
```

**Solutions**:
1. Verify DB-stored password (Edit modal in Accounts page)
2. Check `imap_use_ssl` flag matches port (993=SSL, 143=STARTTLS)
3. Ensure `imap_username` = full email address
4. Verify provider hasn't locked account

### Hostinger Connection Issues
**Symptom**: Gmail works but Hostinger fails

**Solution**:
```bash
# Verify Hostinger settings
# SMTP: Port 465 with SSL (not 587)
# IMAP: Port 993 with SSL
# Username: Full email address (mcintyre@corrinbox.com)
```

**Test**:
```bash
python scripts/test_permanent_accounts.py
```

### Browser JavaScript Errors
**Symptom**: `$ is not defined` or jQuery errors

**Solution**:
- Remove jQuery dependencies from code
- Use Bootstrap 5 Modal API only
- Check `static/js/app.js` for conflicts

## Error Taxonomy & Recovery

### IMAP Errors

**AUTHENTICATIONFAILED**:
- **Cause**: Invalid credentials or disabled IMAP
- **Recovery**: Update credentials via Edit modal
- **Prevention**: Use App Passwords, verify IMAP enabled

**TIMEOUT / Connection Reset**:
- **Cause**: Network issues, server timeout
- **Recovery**: Automatic reconnection with exponential backoff
- **Prevention**: Check network connectivity, firewall rules

**MOVE Unsupported**:
- **Cause**: Provider doesn't support MOVE command
- **Recovery**: Automatic fallback to COPY+DELETE
- **Prevention**: None - automatic handling

### SMTP Errors

**SMTPAuthenticationError**:
- **Cause**: Invalid SMTP credentials
- **Recovery**: Update password, verify App Password
- **Prevention**: Use correct SMTP port and encryption

**SMTPServerDisconnected / Timeout**:
- **Cause**: Network interruption or server timeout
- **Recovery**: Automatic retry after reconnect
- **Prevention**: Check network stability

**STARTTLS Failure on Port 587**:
- **Cause**: SSL wrapper used instead of STARTTLS
- **Recovery**: Ensure `smtp_use_ssl=0` for port 587
- **Prevention**: Use smart detection API

### Database Errors

**Database is Locked**:
- **Cause**: Concurrent write operations
- **Recovery**: WAL mode + busy_timeout automatically retry
- **Prevention**: Already mitigated by WAL mode

**Foreign Key Constraint Failed**:
- **Cause**: Referential integrity violation
- **Recovery**: Check parent records exist before insert
- **Prevention**: Enable foreign keys in all connections

## IMAP Watcher Lifecycle & Debugging

### Connection Process

1. Load account config from DB → prefer `imap_username` else `email_address`
2. Establish connection:
   - SSL: `imaplib.IMAP4_SSL(host, port=993)`
   - STARTTLS: `IMAP4(host, port=143)` → `starttls()`
3. LOGIN with username/password
4. SELECT INBOX
5. IDLE loop (or noop polling fallback)
6. On new message: FETCH metadata, MOVE to Quarantine
7. Heartbeat every N minutes
8. On errors: exponential backoff (1s→2s→4s→... cap 5 min)
9. Graceful close on thread stop

### Common Auth Failures

**Wrong imap_username**:
- **Fix**: Edit modal → set to full email address
- **Test**: `python scripts/verify_accounts.py`

**STARTTLS vs SSL Mismatch**:
- **Fix**: Ensure `imap_use_ssl` matches port
  - Port 993 → `imap_use_ssl=1` (SSL)
  - Port 143 → `imap_use_ssl=0` (STARTTLS)

**Provider Lockouts**:
- **Fix**: Enable App Passwords, verify IMAP enabled
- **Test**: Log in via webmail to check for security notices

## SMTP Send Pipeline Debugging

### Send Process

1. Resolve settings (`smtp_host`/`port`/`use_ssl`/`username`)
2. Connect:
   - Port 465: `smtplib.SMTP_SSL`
   - Port 587: `smtplib.SMTP` → `ehlo` → `starttls` → `ehlo`
3. AUTH (LOGIN/PLAIN via `smtplib.login`)
4. `sendmail(from, to_list, data)`
5. On success: INSERT SENT record, log audit SEND
6. On failure: Map exceptions to user-friendly messages

### Common SMTP Issues

**Authentication Error**:
- **Fix**: Update password, use App Password
- **Test**: `python scripts/test_permanent_accounts.py`

**Server Disconnected**:
- **Fix**: Automatic retry after reconnect
- **Verify**: Check SMTP host/port are correct

**STARTTLS Failure**:
- **Fix**: Ensure port 587 uses `smtp_use_ssl=0`
- **Verify**: Use smart detection API for settings

## Observability & Health

### Log Files

**Application Log** (`app.log`):
- Text format with timestamps
- SMTP/IMAP events, auth failures, actions
- Rotation: 10MB max, 5 backups

**JSON Log** (`logs/app.json.log`):
- Structured format for parsing
- Sample record:
  ```json
  {"timestamp":"2025-10-15T02:55:14.512Z","level":"INFO","logger":"app.routes.interception","message":"[interception::release] success","email_id":123}
  ```

### Useful Log Filters

```bash
# IMAP release failures
jq 'select(.message|test("interception::release") and .level=="ERROR")' logs/app.json.log

# SMTP connection issues grouped by host
jq -r 'select(.message|test("smtp")) | .host' logs/app.json.log | sort | uniq -c

# Failed login attempts
grep -i "authentication failed" app.log

# Rate limit triggers
grep -i "rate limit" app.log
```

### Health Endpoint

```bash
# Check application health
curl http://localhost:5000/healthz
```

**Response Fields**:
- `ok` - Overall health (true/false)
- `db` - Database connectivity ("ok" or null)
- `held_count` - Messages currently held
- `released_24h` - Messages released in last 24 hours
- `median_latency_ms` - Median processing latency
- `workers` - IMAP watcher heartbeats
- `timestamp` - ISO 8601 UTC timestamp

### Rate Limit Monitoring

**Default Limits**:
- Login: 5 attempts per minute
- Release API: 30 per minute
- Edit API: 30 per minute
- Fetch emails: 30 per minute

**429 Response Handling**:
```javascript
if (response.status === 429) {
  const retryAfter = Number(response.headers.get('Retry-After') || 1);
  toast.warning(`Too many requests – retry in ${retryAfter}s`);
  setTimeout(retryCall, retryAfter * 1000);
}
```

## Nothing Works Troubleshooting

### Symptom: Nothing works, /healthz returns 500

**Diagnosis**:
```bash
# Check if app is running
tasklist | findstr python.exe

# Check SMTP proxy thread
netstat -an | findstr :8587

# Check logs
tail -f app.log
```

**Solutions**:
1. Restart application: `python simple_app.py`
2. Verify port 8587 not blocked by firewall
3. Check database file exists: `ls email_manager.db`
4. Verify `key.txt` exists (encryption key)

### Symptom: Web UI loads but no emails appear

**Diagnosis**:
```bash
# Check database
sqlite3 email_manager.db "SELECT COUNT(*) FROM email_messages;"

# Check IMAP watchers
python scripts/verify_accounts.py

# Check logs for IMAP errors
grep -i "imap" app.log
```

**Solutions**:
1. Verify accounts are active: Check Accounts page
2. Start IMAP watchers: Click "Start Monitoring" on Accounts page
3. Check IMAP credentials: Use Edit modal to update passwords

### Symptom: Emails stuck in HELD status

**Diagnosis**:
```bash
# Check held messages
sqlite3 email_manager.db "SELECT COUNT(*) FROM email_messages WHERE interception_status='HELD';"

# Check release endpoint
curl -X POST http://localhost:5000/api/interception/release/1
```

**Solutions**:
1. Verify original_uid is set (should not be 0 or null)
2. Check Quarantine folder exists in email account
3. Review logs for IMAP release errors
4. Manually release via dashboard

## Provider Matrix & Connection Strategy

**Gmail**:
- SMTP: 587 STARTTLS (`smtp_use_ssl=0`)
- IMAP: 993 SSL (`imap_use_ssl=1`)
- Requires: App Password
- Username: Full email address

**Hostinger**:
- SMTP: 465 SSL (`smtp_use_ssl=1`)
- IMAP: 993 SSL (`imap_use_ssl=1`)
- Username: Full email address

**Outlook**:
- SMTP: 587 STARTTLS (`smtp_use_ssl=0`)
- IMAP: 993 SSL (`imap_use_ssl=1`)
- Requires: App Password for 2FA accounts

**Yahoo**:
- SMTP: 465 SSL (`smtp_use_ssl=1`)
- IMAP: 993 SSL (`imap_use_ssl=1`)

**Rules of Thumb**:
- Port 587 → STARTTLS (`smtp_use_ssl=0`, `starttls=True`)
- Port 465 → SSL (`smtp_use_ssl=1`, no STARTTLS)
- Port 993 → SSL (`imap_use_ssl=1`)

## Performance Issues

### Slow Dashboard Loading

**Diagnosis**:
```bash
# Check database size
ls -lh email_manager.db

# Check indices
python scripts/verify_indices.py

# Check query plans
sqlite3 email_manager.db "EXPLAIN QUERY PLAN SELECT * FROM email_messages WHERE status='PENDING';"
```

**Solutions**:
1. Verify indices exist (run migration if needed)
2. Vacuum database: `sqlite3 email_manager.db "VACUUM;"`
3. Clear old emails: Archive and delete old messages

### High Memory Usage

**Diagnosis**:
```bash
# Check IMAP watcher threads
# Each watcher maintains persistent connection
ps aux | grep python
```

**Solutions**:
1. Disable unused accounts (set `is_active=0`)
2. Restart application to clear memory
3. Review IMAP watcher count (one per active account)

## Related Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide
- **[SECURITY.md](SECURITY.md)** - Security configuration
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[TESTING.md](TESTING.md)** - Testing strategy
