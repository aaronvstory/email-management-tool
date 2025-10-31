# Link and Form Audit - Categorized by Feature Area

## Summary
- Total href attributes: 200+
- Total action attributes: 4
- Templates analyzed: 24 files

---

## 1. EMAILS Feature Area

### Primary Templates
- `templates/emails_unified.html`
  - `/compose` (btn-secondary) → NEEDS: url_for('compose.compose_email')

- `templates/email_queue.html`
  - `/emails?status=PENDING` → NEEDS: url_for('emails.email_queue', status='PENDING')
  - `/emails?status=APPROVED` → NEEDS: url_for('emails.email_queue', status='APPROVED')
  - `/emails?status=REJECTED` → NEEDS: url_for('emails.email_queue', status='REJECTED')
  - `/emails?status=ALL` → NEEDS: url_for('emails.email_queue', status='ALL')
  - `/email/{{ email.id }}` → NEEDS: url_for('emails.email_detail', id=email.id)

- `templates/email_viewer.html`
  - `/inbox` → NEEDS: url_for('inbox.inbox_view')
  - `/api/email/${emailId}/reply-forward?action=reply` → OK (API endpoint)
  - `/api/email/${emailId}/reply-forward?action=forward` → OK (API endpoint)

### Stitch Variants (GOOD - using url_for)
- `templates/stitch/emails-unified.html`
  - `url_for('accounts.add_email_account')` ✅
  - Tabs: All hardcoded `href="#"` → NEEDS: proper status filtering

---

## 2. ACCOUNTS Feature Area

### Primary Templates
- `templates/accounts.html`
  - `/accounts/add` (hardcoded) → NEEDS: url_for('accounts.add_email_account')
  - `/accounts/import` (hardcoded) → NEEDS: url_for('accounts.import_page')

- `templates/accounts_import.html`
  - `action="{{ url_for('accounts.api_import_accounts') }}"` ✅ GOOD

### Stitch Variants
- `templates/stitch/accounts.html`
  - `url_for('accounts.add_email_account')` ✅ GOOD

---

## 3. COMPOSE Feature Area

### Primary Templates
- `templates/compose.html`
  - `/emails-unified` (hardcoded btn) → NEEDS: url_for('emails.emails_unified')
  - `action="/compose"` (hardcoded form) → NEEDS: url_for('compose.compose_email')

### Stitch Variants
- `templates/stitch/compose-email.html`
  - `action="{{ url_for('compose.compose_email') }}"` ✅ GOOD
  - `url_for('emails.emails_unified_stitch')` ✅ GOOD

---

## 4. INTERCEPTION Feature Area

### Primary Templates
- `templates/inbox.html`
  - `/compose` → NEEDS: url_for('compose.compose_email')
  - `/interception` → NEEDS: url_for('interception.interception_view')

---

## 5. NAVIGATION (base.html) - CRITICAL

All hardcoded routes in sidebar navigation:
- `/dashboard` → NEEDS: url_for('dashboard.dashboard')
- `/emails-unified` → NEEDS: url_for('emails.emails_unified')
- `/compose` → NEEDS: url_for('compose.compose_email')
- `/watchers` → NEEDS: url_for('watchers.watchers_view')
- `/rules` → NEEDS: url_for('moderation.rules')
- `/accounts` → NEEDS: url_for('accounts.email_accounts')
- `/accounts/import` → NEEDS: url_for('accounts.import_page')
- `/diagnostics` → NEEDS: url_for('diagnostics.diagnostics_view')
- `/settings` → NEEDS: url_for('settings.settings_view')
- `/styleguide` → NEEDS: url_for('styleguide.stitch_styleguide')
- `/interception-test` → NEEDS: url_for('interception.test_page')
- `/logout` → NEEDS: url_for('auth.logout')
- `/login` → NEEDS: url_for('auth.login')

---

## 6. WATCHERS Feature Area

### Primary Templates
- `templates/watchers.html`
  - `/settings` → NEEDS: url_for('settings.settings_view')

---

## 7. SETTINGS Feature Area

### Primary Templates
- `templates/settings.html`
  - `/watchers` (multiple) → NEEDS: url_for('watchers.watchers_view')

---

## 8. STYLEGUIDE Feature Area

### Stitch Variants
- `templates/styleguide/stitch.html`
  - `url_for('emails.emails_unified_stitch')` ✅ GOOD
  - `url_for('accounts.add_email_account')` ✅ GOOD

---

## 9. LEGACY/UNUSED (templates/new/*)

All files in `templates/new/` directory use placeholder `href="#"` links:
- `accounts.html`
- `compose-email.html`
- `emails-unified.html`
- `rules.html`
- `styleguide.html`
- `watchers.html`

**ACTION:** These appear to be design mockups. Verify if still needed or archive.

---

## 10. EXTERNAL RESOURCES (OK - no action needed)

CSS/Font CDN links in base.html and login.html:
- Google Fonts (Inter, Material Symbols)
- Bootstrap 5.3.2 CDN
- Bootstrap Icons

---

## PRIORITY BREAKDOWN

### HIGH PRIORITY (Breaking functionality)
1. **base.html navigation** - 13 hardcoded routes affecting all pages
2. **emails_unified.html** - Main email list page
3. **compose.html** - Email composition form action
4. **accounts.html** - Account management buttons

### MEDIUM PRIORITY (User workflows)
5. **email_queue.html** - Status filtering tabs
6. **inbox.html** - Navigation buttons
7. **watchers.html** - Settings link
8. **settings.html** - Watchers link

### LOW PRIORITY (Already good or mockups)
9. Stitch templates (mostly correct with url_for)
10. templates/new/* (design mockups, not in active use)

---

## Required Stitch Route Variants (Task 11.4 prep)

Based on hardcoded routes, need to create:
- `emails.emails_unified_stitch` ✅ (already exists)
- `compose.compose_email_stitch`
- `accounts.email_accounts_stitch`
- `accounts.import_page_stitch`
- `watchers.watchers_view_stitch`
- `moderation.rules_stitch`
- `diagnostics.diagnostics_view_stitch`
- `settings.settings_view_stitch`
- `interception.test_page_stitch`
- `styleguide.stitch_styleguide_stitch`
