# Legacy and Broken Links - Detailed Documentation

## Definition Criteria
**Legacy**: Hardcoded routes not using Flask's `url_for()` helper
**Broken**: Links pointing to non-existent routes or using incorrect blueprints

---

## CRITICAL ISSUES (Must Fix Immediately)

### 1. base.html - Global Navigation (ALL PAGES AFFECTED)
**Impact**: Every authenticated page inherits these broken links
**Count**: 13 hardcoded routes

| Link | Current | Required Fix | Blueprint |
|------|---------|--------------|-----------|
| Dashboard | `/dashboard` | `url_for('dashboard.dashboard')` | dashboard_bp |
| Emails | `/emails-unified` | `url_for('emails.emails_unified')` | emails_bp |
| Compose | `/compose` | `url_for('compose.compose_email')` | compose_bp |
| Watchers | `/watchers` | `url_for('watchers.watchers_view')` | watchers_bp |
| Rules | `/rules` | `url_for('moderation.rules')` | moderation_bp |
| Accounts | `/accounts` | `url_for('accounts.email_accounts')` | accounts_bp |
| Import | `/accounts/import` | `url_for('accounts.import_page')` | accounts_bp |
| Diagnostics | `/diagnostics` | `url_for('diagnostics.diagnostics_view')` | diagnostics_bp |
| Settings | `/settings` | `url_for('settings.settings_view')` | settings_bp |
| Styleguide | `/styleguide` | `url_for('styleguide.stitch_styleguide')` | styleguide_bp |
| Interception | `/interception-test` | `url_for('interception.test_page')` | interception_bp |
| Logout | `/logout` | `url_for('auth.logout')` | auth_bp |
| Login | `/login` | `url_for('auth.login')` | auth_bp |

**File**: `templates/base.html` lines 88-190
**Severity**: HIGH - Affects all pages

---

### 2. compose.html - Form Action
**Issue**: Hardcoded POST action

```html
<!-- CURRENT (BROKEN) -->
<form method="POST" action="/compose" id="composeForm">

<!-- REQUIRED FIX -->
<form method="POST" action="{{ url_for('compose.compose_email') }}" id="composeForm">
```

**File**: `templates/compose.html` line 36
**Severity**: HIGH - Breaks email composition

---

### 3. accounts.html - Action Buttons
**Issue**: Hardcoded button links

```html
<!-- CURRENT (BROKEN) -->
<a href="/accounts/add" class="btn btn-secondary btn-sm">
<a href="/accounts/import" class="btn btn-secondary btn-sm">

<!-- REQUIRED FIX -->
<a href="{{ url_for('accounts.add_email_account') }}" class="btn btn-secondary btn-sm">
<a href="{{ url_for('accounts.import_page') }}" class="btn btn-secondary btn-sm">
```

**File**: `templates/accounts.html` lines 22, 25
**Severity**: HIGH - Blocks account management

---

## MODERATE ISSUES (User Workflows Affected)

### 4. emails_unified.html - Compose Button
```html
<!-- CURRENT -->
<a href="/compose" class="btn btn-secondary btn-sm">

<!-- FIX -->
<a href="{{ url_for('compose.compose_email') }}" class="btn btn-secondary btn-sm">
```
**File**: `templates/emails_unified.html` line 16

---

### 5. email_queue.html - Status Filter Tabs
**Issue**: All status filter links hardcoded

```html
<!-- CURRENT -->
<a href="/emails?status=PENDING">
<a href="/emails?status=APPROVED">
<a href="/emails?status=REJECTED">
<a href="/emails?status=ALL">

<!-- FIX -->
<a href="{{ url_for('emails.email_queue', status='PENDING') }}">
<a href="{{ url_for('emails.email_queue', status='APPROVED') }}">
<a href="{{ url_for('emails.email_queue', status='REJECTED') }}">
<a href="{{ url_for('emails.email_queue', status='ALL') }}">
```
**File**: `templates/email_queue.html` lines 55, 63, 71, 79

---

### 6. email_queue.html - View Email Button
```html
<!-- CURRENT -->
<a href="/email/{{ email.id }}" class="btn btn-sm btn-outline-primary">

<!-- FIX -->
<a href="{{ url_for('emails.email_detail', id=email.id) }}" class="btn btn-sm btn-outline-primary">
```
**File**: `templates/email_queue.html` line 133

---

### 7. email_viewer.html - Back to Inbox
```html
<!-- CURRENT -->
<a href="/inbox" class="btn btn-ghost btn-sm">

<!-- FIX -->
<a href="{{ url_for('inbox.inbox_view') }}" class="btn btn-ghost btn-sm">
```
**File**: `templates/email_viewer.html` line 14

---

### 8. inbox.html - Navigation Buttons
```html
<!-- CURRENT -->
<a href="/compose" class="btn btn-secondary btn-sm">
<a href="/interception" class="btn btn-ghost btn-sm">

<!-- FIX -->
<a href="{{ url_for('compose.compose_email') }}" class="btn btn-secondary btn-sm">
<a href="{{ url_for('interception.interception_view') }}" class="btn btn-ghost btn-sm">
```
**File**: `templates/inbox.html` lines 27, 30

---

### 9. watchers.html - Settings Link
```html
<!-- CURRENT -->
<a href="/settings" class="btn btn-ghost btn-sm">

<!-- FIX -->
<a href="{{ url_for('settings.settings_view') }}" class="btn btn-ghost btn-sm">
```
**File**: `templates/watchers.html` line 12

---

### 10. settings.html - Watchers Links
```html
<!-- CURRENT -->
<a href="/watchers" class="btn btn-ghost btn-sm">
<a class="btn btn-secondary btn-sm" href="/watchers" onclick="...">

<!-- FIX -->
<a href="{{ url_for('watchers.watchers_view') }}" class="btn btn-ghost btn-sm">
<a class="btn btn-secondary btn-sm" href="{{ url_for('watchers.watchers_view') }}" onclick="...">
```
**File**: `templates/settings.html` lines 15, 23

---

## LOW PRIORITY (Design Mockups / Not in Production)

### 11. templates/new/* Directory
**All files contain placeholder links**: `href="#"`

Files affected:
- `templates/new/accounts.html`
- `templates/new/compose-email.html`
- `templates/new/emails-unified.html`
- `templates/new/rules.html`
- `templates/new/styleguide.html`
- `templates/new/watchers.html`

**Recommendation**: Archive or delete - these appear to be design prototypes

---

### 12. partials/account_components.html
```html
<!-- CURRENT -->
<a href="/accounts/add" class="alert-link">

<!-- FIX -->
<a href="{{ url_for('accounts.add_email_account') }}" class="alert-link">
```
**File**: `templates/partials/account_components.html` lines 102, 211

---

## ALREADY CORRECT (No Action Needed)

### Stitch Templates Using url_for ✅
- `templates/stitch/accounts.html` - Correct
- `templates/stitch/compose-email.html` - Correct
- `templates/stitch/emails-unified.html` - Correct
- `templates/styleguide/stitch.html` - Correct
- `templates/accounts_import.html` - Form action correct

### Stitch Templates with Minor Issues
- `templates/stitch/emails-unified.html` lines 50-53
  - Tab links still use `href="#"` instead of status filtering
  - **FIX**: Implement proper status query params

---

## SUMMARY BY SEVERITY

| Severity | Count | Templates Affected |
|----------|-------|-------------------|
| **CRITICAL** | 16 | base.html (13), compose.html (1), accounts.html (2) |
| **MODERATE** | 12 | emails_unified, email_queue, email_viewer, inbox, watchers, settings |
| **LOW** | 50+ | templates/new/* (design mockups), partials |

**Total Legacy/Broken Links**: 78+
**Immediate Action Required**: 16 (Critical)

---

## BLUEPRINT VERIFICATION CHECKLIST

Before refactoring, verify these blueprints exist and routes are registered:

- [ ] `dashboard_bp` - `/dashboard` route
- [ ] `emails_bp` - `/emails-unified`, `/email/<id>`, `/email-queue` routes
- [ ] `compose_bp` - `/compose` route
- [ ] `watchers_bp` - `/watchers` route
- [ ] `moderation_bp` - `/rules` route
- [ ] `accounts_bp` - `/accounts`, `/accounts/add`, `/accounts/import` routes
- [ ] `diagnostics_bp` - `/diagnostics` route
- [ ] `settings_bp` - `/settings` route
- [ ] `styleguide_bp` - `/styleguide` route
- [ ] `interception_bp` - `/interception-test`, `/interception` routes
- [ ] `inbox_bp` - `/inbox` route
- [ ] `auth_bp` - `/login`, `/logout` routes

**Next Step**: Cross-reference with `app/routes/` directory structure
