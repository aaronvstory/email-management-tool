# Stitch Route Implementation Checklist

## EXISTING ROUTES ✅ (5)
- [x] `email_accounts_stitch()` - accounts.py
- [x] `compose_stitch()` - compose.py
- [x] `emails_unified_stitch()` - emails.py
- [x] `rules_stitch()` - moderation.py
- [x] `watchers_page_stitch()` - watchers.py

## HIGH PRIORITY - TO IMPLEMENT (12)

### Dashboard (1)
- [ ] `dashboard_stitch()` - dashboard.py
  - Template: `stitch/dashboard.html` (create)

### Emails (3)
- [ ] `email_detail_stitch(id)` - emails.py
  - Template: `stitch/email-detail.html` (create)
- [ ] `email_edit_stitch(id)` - emails.py
  - Template: `stitch/email-edit.html` (create)
- [ ] `email_queue_stitch()` - emails.py
  - Template: `stitch/email-queue.html` (create)

### Accounts (2)
- [ ] `add_email_account_stitch()` - accounts.py
  - Template: `stitch/account-add.html` (create)
- [ ] `import_page_stitch()` - accounts.py
  - Template: Exists: `accounts_import.html` (verify Stitch-ified)

### Interception (4)
- [ ] `test_page_stitch()` - interception.py **NEW FEATURE**
  - Template: `stitch/interception-test.html` (create)
- [ ] `release_stitch(id)` - interception.py
  - Template: Redirect only (no template)
- [ ] `discard_stitch(id)` - interception.py
  - Template: Redirect only (no template)
- [ ] `interception_view_stitch()` - interception.py
  - Template: `stitch/interception.html` (create)

### Diagnostics (2)
- [ ] `diagnostics_view_stitch()` - diagnostics.py **NEW FEATURE**
  - Template: `stitch/diagnostics.html` (create with live logs)

## MEDIUM PRIORITY - TO IMPLEMENT (10)

### Inbox (1)
- [ ] `inbox_view_stitch()` - inbox.py
  - Template: `stitch/inbox.html` (create)

### Settings (1)
- [ ] `settings_view_stitch()` - settings.py
  - Template: `stitch/settings.html` (create)

### Moderation (2)
- [ ] `add_rule_stitch()` - moderation.py
  - Template: `stitch/rule-add.html` (create)
- [ ] `edit_rule_stitch(id)` - moderation.py
  - Template: `stitch/rule-edit.html` (create)

### Accounts (2)
- [ ] `edit_account_stitch(id)` - accounts.py
  - Template: `stitch/account-edit.html` (create)
- [ ] `delete_account_stitch(id)` - accounts.py
  - Template: Redirect only (POST only)

## IMPLEMENTATION ORDER

**Phase 1 (Start here):**
1. dashboard_stitch() - Simple view
2. email_detail_stitch(id) - Critical for email viewing
3. release_stitch(id) / discard_stitch(id) - Critical actions (no templates)

**Phase 2:**
4. email_edit_stitch(id) - Email editing
5. add_email_account_stitch() - Account creation

**Phase 3 (NEW FEATURES - Complex):**
6. test_page_stitch() - Interception test page
7. diagnostics_view_stitch() - Diagnostics + live logs

**Phase 4 (Remaining):**
8. All MEDIUM priority routes

## Templates to Create Summary

### HIGH Priority (8 templates)
1. stitch/dashboard.html
2. stitch/email-detail.html
3. stitch/email-edit.html
4. stitch/email-queue.html
5. stitch/account-add.html
6. stitch/interception-test.html ⭐ NEW
7. stitch/interception.html
8. stitch/diagnostics.html ⭐ NEW

### MEDIUM Priority (7 templates)
9. stitch/inbox.html
10. stitch/settings.html
11. stitch/rule-add.html
12. stitch/rule-edit.html
13. stitch/account-edit.html

## Next Steps
Start with Phase 1 - dashboard, email_detail, release/discard actions
