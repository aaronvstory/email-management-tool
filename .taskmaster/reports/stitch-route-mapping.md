# /stitch Route Variants Mapping

## Purpose
Map every legacy hardcoded route to its required /stitch variant for the Stitch design system migration.

---

## IMPLEMENTATION REQUIREMENTS

### Route Naming Convention
- Original route: `/emails-unified`
- Stitch variant: `/emails-unified/stitch` or named route ending in `_stitch`
- Blueprint method: `emails_unified_stitch()`

### Response Pattern
- All `/stitch` routes render templates from `templates/stitch/` directory
- Use Stitch macros from `templates/stitch/_macros.html`
- Maintain dark theme with lime accent (#bef264)
- Square corners, no Bootstrap legacy styles

---

## ROUTE MAPPING TABLE

### Dashboard Blueprint (`app/routes/dashboard.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority |
|-------------|---------------------|-------------|----------|----------|
| `/dashboard` | `/dashboard/stitch` | `dashboard_stitch()` | `stitch/dashboard.html` | HIGH |

---

### Emails Blueprint (`app/routes/emails.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/emails-unified` | `/emails-unified/stitch` | `emails_unified_stitch()` | `stitch/emails-unified.html` | HIGH | ✅ EXISTS |
| `/email/<int:id>` | `/email/<int:id>/stitch` | `email_detail_stitch(id)` | `stitch/email-detail.html` | HIGH | NEEDED |
| `/email/<int:id>/edit` | `/email/<int:id>/edit/stitch` | `email_edit_stitch(id)` | `stitch/email-edit.html` | HIGH | NEEDED |
| `/emails` (queue) | `/emails/stitch` | `email_queue_stitch()` | `stitch/email-queue.html` | MEDIUM | NEEDED |

**Additional Parameters:**
- `/emails/stitch?status=<filter>` - Support PENDING/APPROVED/REJECTED/ALL filtering

---

### Compose Blueprint (`app/routes/compose.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/compose` (GET) | `/compose/stitch` | `compose_email_stitch()` | `stitch/compose-email.html` | HIGH | ✅ EXISTS |
| `/compose` (POST) | `/compose/stitch` | `compose_email_stitch()` | Redirect after success | HIGH | ✅ EXISTS |

---

### Accounts Blueprint (`app/routes/accounts.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/accounts` | `/accounts/stitch` | `email_accounts_stitch()` | `stitch/accounts.html` | HIGH | ✅ EXISTS |
| `/accounts/add` | `/accounts/add/stitch` | `add_email_account_stitch()` | `stitch/account-add.html` | HIGH | NEEDED |
| `/accounts/import` | `/accounts/import/stitch` | `import_page_stitch()` | `stitch/accounts-import.html` | HIGH | NEEDED |
| `/accounts/<int:id>/edit` | `/accounts/<int:id>/edit/stitch` | `edit_account_stitch(id)` | `stitch/account-edit.html` | MEDIUM | NEEDED |
| `/accounts/<int:id>/delete` | `/accounts/<int:id>/delete/stitch` | `delete_account_stitch(id)` | Redirect (POST only) | MEDIUM | NEEDED |

---

### Interception Blueprint (`app/routes/interception.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/interception` | `/interception/stitch` | `interception_view_stitch()` | `stitch/interception.html` | MEDIUM | NEEDED |
| `/interception-test` | `/interception-test/stitch` | `test_page_stitch()` | `stitch/interception-test.html` | HIGH | NEEDED (NEW FEATURE) |
| `/interception/release/<int:id>` | `/interception/release/<int:id>/stitch` | `release_stitch(id)` | Redirect (POST) | HIGH | NEEDED |
| `/interception/discard/<int:id>` | `/interception/discard/<int:id>/stitch` | `discard_stitch(id)` | Redirect (POST) | HIGH | NEEDED |

---

### Inbox Blueprint (`app/routes/inbox.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/inbox` | `/inbox/stitch` | `inbox_view_stitch()` | `stitch/inbox.html` | MEDIUM | NEEDED |

---

### Watchers Blueprint (`app/routes/watchers.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/watchers` | `/watchers/stitch` | `watchers_view_stitch()` | `stitch/watchers.html` | MEDIUM | NEEDED |

---

### Moderation Blueprint (`app/routes/moderation.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/rules` | `/rules/stitch` | `rules_stitch()` | `stitch/rules.html` | MEDIUM | NEEDED |
| `/rules/add` | `/rules/add/stitch` | `add_rule_stitch()` | `stitch/rule-add.html` | MEDIUM | NEEDED |
| `/rules/<int:id>/edit` | `/rules/<int:id>/edit/stitch` | `edit_rule_stitch(id)` | `stitch/rule-edit.html` | MEDIUM | NEEDED |

---

### Settings Blueprint (`app/routes/settings.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/settings` | `/settings/stitch` | `settings_view_stitch()` | `stitch/settings.html` | MEDIUM | NEEDED |

---

### Diagnostics Blueprint (`app/routes/diagnostics.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/diagnostics` | `/diagnostics/stitch` | `diagnostics_view_stitch()` | `stitch/diagnostics.html` | HIGH | NEEDED (NEW FEATURE) |

---

### Styleguide Blueprint (`app/routes/styleguide.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/styleguide` | `/styleguide/stitch` | `stitch_styleguide()` | `styleguide/stitch.html` | LOW | ✅ EXISTS |

---

### Auth Blueprint (`app/routes/auth.py`)

| Legacy Route | Stitch Variant Route | Method Name | Template | Priority | Status |
|-------------|---------------------|-------------|----------|----------|--------|
| `/login` | `/login` | `login()` | `login.html` | N/A | NO STITCH (pre-auth) |
| `/logout` | `/logout` | `logout()` | Redirect | N/A | NO STITCH (action only) |

---

## SUMMARY STATISTICS

| Priority | Routes Needed | Templates Needed | Already Exist |
|----------|--------------|------------------|---------------|
| **HIGH** | 12 | 10 | 3 ✅ |
| **MEDIUM** | 10 | 9 | 0 |
| **LOW** | 0 | 0 | 1 ✅ |
| **Total** | **22** | **19** | **4** |

---

## IMPLEMENTATION CHECKLIST (Task 12)

### Phase 1: High Priority Routes (Required for core functionality)
- [ ] `/dashboard/stitch` - Dashboard view
- [ ] `/email/<int:id>/stitch` - Email detail view
- [ ] `/email/<int:id>/edit/stitch` - Email edit form
- [ ] `/accounts/add/stitch` - Add account form
- [ ] `/accounts/import/stitch` - Import accounts page
- [ ] `/interception-test/stitch` - NEW: Interception testing page
- [ ] `/interception/release/<int:id>/stitch` - Release email action
- [ ] `/interception/discard/<int:id>/stitch` - Discard email action
- [ ] `/diagnostics/stitch` - NEW: Diagnostics & live logs

### Phase 2: Medium Priority Routes (User workflows)
- [ ] `/emails/stitch` - Email queue with status filters
- [ ] `/inbox/stitch` - Inbox view
- [ ] `/watchers/stitch` - Watchers management
- [ ] `/rules/stitch` - Rules listing
- [ ] `/rules/add/stitch` - Add rule form
- [ ] `/rules/<int:id>/edit/stitch` - Edit rule form
- [ ] `/settings/stitch` - Settings page
- [ ] `/accounts/<int:id>/edit/stitch` - Edit account form
- [ ] `/accounts/<int:id>/delete/stitch` - Delete account action
- [ ] `/interception/stitch` - Interception management

---

## TEMPLATE REQUIREMENTS

### Templates Already Exist ✅
- `templates/stitch/emails-unified.html`
- `templates/stitch/compose-email.html`
- `templates/stitch/accounts.html`
- `templates/styleguide/stitch.html`

### Templates to Create (Priority Order)

**HIGH:**
1. `templates/stitch/dashboard.html`
2. `templates/stitch/email-detail.html`
3. `templates/stitch/email-edit.html`
4. `templates/stitch/account-add.html`
5. `templates/stitch/accounts-import.html`
6. `templates/stitch/interception-test.html` (NEW FEATURE)
7. `templates/stitch/diagnostics.html` (NEW FEATURE)

**MEDIUM:**
8. `templates/stitch/email-queue.html`
9. `templates/stitch/inbox.html`
10. `templates/stitch/watchers.html`
11. `templates/stitch/rules.html`
12. `templates/stitch/rule-add.html`
13. `templates/stitch/rule-edit.html`
14. `templates/stitch/settings.html`
15. `templates/stitch/account-edit.html`
16. `templates/stitch/interception.html`

---

## BLUEPRINT VERIFICATION

Before implementing routes, verify blueprint registration in `simple_app.py`:

```python
# Expected blueprint registrations
app.register_blueprint(dashboard_bp)
app.register_blueprint(emails_bp)
app.register_blueprint(compose_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(interception_bp)
app.register_blueprint(inbox_bp)
app.register_blueprint(watchers_bp)
app.register_blueprint(moderation_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(diagnostics_bp)  # May need to create
app.register_blueprint(styleguide_bp)
app.register_blueprint(auth_bp)
```

---

## MACRO USAGE REQUIREMENTS

All Stitch templates must import and use these macros from `templates/stitch/_macros.html`:

```jinja
{% from 'stitch/_macros.html' import badge, icon_btn, table, toolbar, alert, form_field, modal, pagination, empty_state %}
```

**Required Usage:**
- `badge()` for status indicators (HELD, FETCHED, RELEASED, etc.)
- `icon_btn()` for all action buttons
- `table()` for data listings
- `toolbar()` for page headers with actions
- `alert()` for success/error messages
- `form_field()` for form inputs
- `modal()` for dialogs
- `pagination()` for page navigation
- `empty_state()` for no-data scenarios

---

## ROUTE IMPLEMENTATION SKELETON

```python
# Example: emails_bp
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required

emails_bp = Blueprint('emails', __name__)

@emails_bp.route('/email/<int:id>/stitch')
@login_required
def email_detail_stitch(id):
    # Fetch email by ID
    email = get_email_or_404(id)
    attachments = get_attachments_for_email(id)

    return render_template('stitch/email-detail.html',
                         email=email,
                         attachments=attachments)

@emails_bp.route('/email/<int:id>/edit/stitch', methods=['GET', 'POST'])
@login_required
def email_edit_stitch(id):
    if request.method == 'POST':
        # Update email
        update_email(id, request.form)
        return redirect(url_for('emails.email_detail_stitch', id=id))

    email = get_email_or_404(id)
    return render_template('stitch/email-edit.html', email=email)
```

---

## NEXT STEPS (Task 12)

1. Verify all blueprints exist in `app/routes/`
2. Create missing blueprints (diagnostics if needed)
3. Implement HIGH priority routes first (12 routes)
4. Create corresponding templates (7 new templates)
5. Test each route manually via Chrome DevTools
6. Implement MEDIUM priority routes (10 routes)
7. Complete remaining templates (9 templates)
8. Full regression testing

**Estimated Time for Task 12:** 90-120 minutes
