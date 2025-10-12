# IMAP Connection Fixes - 2025-10-12

## Summary

Fixed critical IMAP connection issues in `app/services/imap_watcher.py` that caused crashes and authentication failures. The main issue was improper error handling when IMAP connections failed, leading to `NoneType` errors when the client object was `None`.

## Issues Fixed

### 1. NoneType Context Manager Error (Line 230)
**Problem**: When IMAP authentication failed, `_connect()` returned `None`, but the code tried to use it as a context manager: `with client.idle():`

**Root Cause**:
- `_connect()` returns `None` on authentication failure
- `run_forever()` didn't properly validate the client before using it
- The code used context manager syntax that was incompatible with explicit `idle()` calls

**Fix**:
- Changed from context manager (`with client.idle():`) to explicit `client.idle()` / `client.idle_done()` calls
- Added comprehensive `None` checks before every client operation
- Raise `ConnectionError` on initial connection failure to trigger backoff retry
- Added client validation at multiple checkpoints in the main loop

### 2. Authentication Failure Handling
**Problem**: Authentication failures caused silent failures or infinite retry loops without useful error messages

**Fix**:
- Added credential validation before attempting connection (check for empty username/password/host)
- Enhanced error classification with specific reasons: `auth_failed`, `tls_failed`, `timeout`, `connection_refused`, `missing_credentials`, `missing_config`
- Improved error logging with actionable troubleshooting hints
- Update database `last_error` field with detailed error messages
- Added circuit breaker integration via `_record_failure()` to disable accounts after repeated failures

### 3. Connection Recovery
**Problem**: When connections were lost during operation, the watcher would crash or enter an invalid state

**Fix**:
- Added reconnection logic in the main loop with validation
- Reset `self._client = None` on any connection error
- Added continuous client validation before IDLE operations
- Implemented graceful degradation to polling mode for servers without IDLE support
- Added error recovery with exponential backoff via `@backoff` decorator

### 4. Logging and Diagnostics
**Problem**: Insufficient logging made it difficult to diagnose connection issues

**Fix**:
- Added detailed logging at all connection stages
- Masked passwords in logs for security
- Added account_id to all log messages for multi-account debugging
- Created comprehensive diagnostic script (`scripts/diagnose_imap.py`)
- Added provider-specific troubleshooting hints (Gmail App Passwords, etc.)

## Files Modified

### `app/services/imap_watcher.py`

#### `_connect()` method improvements:
```python
# Before attempting connection:
- Validate username, password, and host are not empty
- Record specific failure types (auth_failed, missing_credentials, etc.)
- Update database last_error field with truncated error message
- Provide provider-specific troubleshooting hints in logs

# Error classification:
- AUTHENTICATIONFAILED → auth_failed (check App Passwords for Gmail/Outlook)
- SSL/TLS errors → tls_failed (check port: 993 for SSL, 143 for STARTTLS)
- Timeout → timeout (check firewall, network)
- Connection refused → connection_refused (check host/port settings)
```

#### `run_forever()` method improvements:
```python
# Initial connection:
- Validate self._client is not None
- Raise ConnectionError if connection fails (triggers backoff retry)
- Add detailed logging for connection success

# Main loop:
- Continuous client validation before operations
- Automatic reconnection with validation
- Graceful handling of client becoming None during operation
- Separate error handling for IDLE vs non-IDLE modes
- Proper cleanup on errors (idle_done(), logout())

# IDLE mode:
- Explicit client.idle() / client.idle_done() (not context manager)
- Validate client before and during IDLE
- Handle NOOP failures as connection loss
- Proper error recovery with brief pause
```

## New Files Created

### `scripts/diagnose_imap.py`
Comprehensive IMAP connection diagnostic tool that:
- Tests IMAP connections for all active accounts
- Decrypts passwords from database securely
- Validates credentials and configuration
- Provides actionable troubleshooting steps
- Tests INBOX access and server capabilities
- Reports IDLE and MOVE/UIDPLUS support
- Generates summary for multiple accounts

**Usage:**
```bash
# Test all active accounts
python scripts/diagnose_imap.py

# Test specific account
python scripts/diagnose_imap.py 1
```

## Testing

### Manual Testing
Run the diagnostic script to verify all accounts:
```bash
cd C:\claude\Email-Management-Tool
python scripts/diagnose_imap.py
```

Expected output for working accounts:
```
✅ CONNECTION SUCCESSFUL!
   - Logged in as: user@example.com
   - Server capabilities: (b'IMAP4REV1', b'IDLE', ...)
   - INBOX access: ✓
   - IDLE support: ✓
   - MOVE/UIDPLUS support: ✓

✅ ALL TESTS PASSED - Account is properly configured
```

Expected output for authentication failures:
```
❌ CONNECTION FAILED

TROUBLESHOOTING STEPS:
🔐 AUTHENTICATION FAILURE DETECTED
   1. For Gmail/Outlook: Generate and use an App Password
   2. Verify username is the full email address
   3. Check if account has 2FA enabled (required for app passwords)
   4. Ensure IMAP is enabled in email provider settings
```

### Automated Testing
Existing tests should pass with improved error handling:
```bash
python -m pytest tests/interception/ -v
```

## Configuration Updates

### Environment Variables
No new environment variables required. Existing variables work as before:
- `EMAIL_CONN_TIMEOUT` - Connection timeout in seconds (default: 15, range: 5-60)
- `IMAP_CIRCUIT_THRESHOLD` - Number of failures before disabling account (default: 5)
- `IMAP_LOG_VERBOSE` - Enable verbose IMAP logging (0/1, default: 0)

### Database Schema
No schema changes required. Uses existing columns:
- `email_accounts.last_error` - Updated with detailed error messages
- `email_accounts.last_checked` - Updated on each connection attempt
- `email_accounts.is_active` - Set to 0 by circuit breaker on repeated failures
- `worker_heartbeats.error_count` - Tracks consecutive failures

## Deployment Notes

1. **Stop existing IMAP watchers** before deploying:
   ```bash
   .\manage.ps1 stop
   ```

2. **Deploy updated files**:
   - `app/services/imap_watcher.py` (critical fix)
   - `scripts/diagnose_imap.py` (diagnostic tool)

3. **Test connections**:
   ```bash
   python scripts/diagnose_imap.py
   ```

4. **Re-enable failed accounts** if credentials were fixed:
   ```sql
   UPDATE email_accounts
   SET is_active=1, last_error=NULL
   WHERE id=<account_id>;
   ```

5. **Restart application**:
   ```bash
   .\manage.ps1 start
   ```

## Troubleshooting Guide

### Account 1 Errors (Authentication Failure)
**Error**: `b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)'`

**Common Causes**:
1. Using regular password instead of App Password (Gmail/Outlook)
2. 2FA not enabled or App Password not generated
3. IMAP not enabled in provider settings
4. Incorrect username (should be full email address)

**Solutions**:
1. **Gmail**: Generate App Password at https://myaccount.google.com/apppasswords
2. **Outlook**: Generate App Password at https://account.live.com/proofs/AppPassword
3. **Hostinger**: Use regular password, ensure IMAP is enabled
4. Update credentials in database via Accounts page
5. Re-activate account after fixing: `UPDATE email_accounts SET is_active=1 WHERE id=1;`

### No Active Accounts Found
**Error**: "No active accounts found in database"

**Cause**: All accounts disabled by circuit breaker after repeated failures

**Solution**:
1. Fix credentials for each account
2. Run diagnostic to verify: `python scripts/diagnose_imap.py <account_id>`
3. Re-enable accounts: `UPDATE email_accounts SET is_active=1, last_error=NULL;`

### Connection Timeouts
**Error**: "IMAP connection timeout"

**Solutions**:
1. Check firewall allows outbound connections on port 993 (SSL) or 143 (STARTTLS)
2. Verify IMAP host is correct and reachable
3. Increase timeout: Set `EMAIL_CONN_TIMEOUT=30` in .env
4. Check VPN/proxy interference

## Architecture Improvements

### Defensive Programming
- All client operations wrapped in try/except
- Multiple validation checkpoints before critical operations
- Null checks before every client method call
- Graceful degradation (IDLE → polling)
- Automatic recovery with exponential backoff

### Error Taxonomy
Errors classified into actionable categories:
- `auth_failed` - Wrong credentials, needs App Password
- `tls_failed` - SSL/port configuration issue
- `timeout` - Network/firewall issue
- `connection_refused` - Wrong host/port
- `missing_credentials` - Empty username/password
- `missing_config` - Empty IMAP host

### Circuit Breaker Pattern
- Tracks consecutive failures per account
- Disables account after threshold (default: 5)
- Prevents infinite retry loops
- Requires manual re-enabling after fix

## Future Enhancements

1. **Health Check Dashboard**: Visual display of account health with last_error messages
2. **Auto-Retry**: Periodic retry of disabled accounts (e.g., once per hour)
3. **Credential Validation**: Test credentials before saving to database
4. **Provider Presets**: Auto-configure settings for Gmail/Outlook/Hostinger
5. **Notification System**: Alert admins when accounts fail repeatedly
6. **Metrics**: Track connection success rate, latency, retry frequency

## References

- IMAP RFC 3501: https://tools.ietf.org/html/rfc3501
- IMAPClient Documentation: https://imapclient.readthedocs.io/
- Gmail App Passwords: https://support.google.com/accounts/answer/185833
- Outlook App Passwords: https://support.microsoft.com/en-us/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944
