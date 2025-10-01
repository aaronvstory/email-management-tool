# Deprecated Sieve Components (Archived)

## Status: DEPRECATED as of v2.0

Sieve auto-interception functionality has been fully removed from the Email Management Tool.
All ManageSieve protocol support and server-side filtering has been abandoned in favor of IMAP-only interception.

## What Was Removed

The following components were part of the original dual-mode interception design:

1. **sieve_client.py** - ManageSieve protocol client implementation
2. **sieve_detector.py** - DNS SRV-based Sieve endpoint discovery
3. **sieve_manager.py** - High-level Sieve rule deployment and activation

These files have been replaced with stub modules that raise `RuntimeError` on import to prevent accidental usage.

## Why Was It Removed

- **Complexity**: ManageSieve added significant complexity for minimal benefit
- **Compatibility**: Not all email providers support ManageSieve (Gmail, Outlook, many others)
- **Security**: Sieve scripts running on mail servers introduced additional attack surface
- **Reliability**: IMAP-based interception proved more reliable and portable
- **Maintenance**: Dual-mode support created testing and debugging overhead

## Current Architecture

**IMAP-Only Interception** (v2.0+):
- Persistent IMAP IDLE watchers per account
- Immediate MOVE/COPY+DELETE to Quarantine folder on detection
- Edit + release workflow via APPEND to INBOX
- Latency typically 100-300ms from arrival to interception
- Works with all IMAP-capable providers

## Migration Notes

### For Developers
All Sieve-related code has been stubbed in `app/services/`:
- `sieve_client.py` → raises RuntimeError
- `sieve_detector.py` → raises RuntimeError
- `sieve_manager.py` → raises RuntimeError

Any imports will fail immediately with clear error messages.

### For Database
Legacy columns retained for backward compatibility:
- `email_accounts.sieve_status` (marked 'deprecated')
- `email_accounts.sieve_endpoint` (set to NULL)

These may be dropped in a future migration once downstream tools are updated.

### For Testing
All Sieve-related tests have been removed or disabled.
Test file `tests/test_sieve_removal.py` verifies modules are non-importable.

## Reactivation Policy

Sieve support will **NOT** be reactivated without:
1. Explicit design approval from project maintainers
2. Comprehensive security review
3. Provider compatibility matrix
4. Full test coverage for dual-mode operation
5. Performance benchmarking vs IMAP-only

## Historical Context

Original implementation attempted to use Sieve for:
- Automatic server-side quarantining
- Zero-latency interception
- Minimal IMAP polling overhead

In practice, this proved:
- Difficult to configure (ManageSieve not widely supported)
- Hard to debug (server-side script errors)
- Less reliable than client-side IMAP polling

## References

- **Original Design**: See `archive/deprecated_sieve/original_design.md` (if available)
- **New Architecture**: See `INTERCEPTION_IMPLEMENTATION.md` in project root
- **Migration Guide**: See `MIGRATION_V2.md` for upgrade instructions

## Archive Date

- **Deprecated**: September 30, 2025
- **Version**: v2.0
- **Last Sieve Commit**: Check git history for final Sieve changes before removal

---

**For questions about this decision, contact the project maintainers.**