# CLAUDE.md

## Project Overview

**Email Management Tool** is a Python Flask application for local email interception, moderation, and management. Dev-focused; runs entirely on localhost with SQLite—no cloud services, no Docker required.

**Version**: 2.9.1  
**Status**: 🟢 Fully functional — SMTP proxy running; IMAP watchers using hybrid IDLE+polling strategy; core UI accessible with responsive design.  
**Current Branch**: feat/styleguide-refresh  
**Last Updated**: October 31, 2025

| Component            | Details                                                           |
| -------------------- | ----------------------------------------------------------------- |
| **Web Dashboard**    | http://localhost:5000 (admin / admin123)                          |
| **SMTP Proxy**       | localhost:8587                                                    |
| **Database**         | SQLite (email_manager.db) - local only                          |
| **Encryption**       | Fernet symmetric (key.txt)                                      |
| **Primary Launcher** | EmailManager.bat (menu) or launch.bat (quick)                 |
| **Test Accounts**    | karlkoxwerks@stateauditgroup.com, Hostinger (mcintyre@corrinbox.com) |

⚠️ **Security Note**: Test accounts are for **development/testing only**. Never use in production.

## 🎨 Stitch UI Design System (MANDATORY)

### Absolute Design Rules
- **Primary accent**: lime `#bef264` ONLY. No Bootstrap blues. Red only for destructive actions.
- **Square corners**: No border radius unless explicitly set in component (0px default).
- **Dark surfaces**: `--bg: #18181b`, `--surface: #27272a`, `--border: rgba(255,255,255,.12)`
- **Tailwind utilities**: prefix `tw-`, preflight disabled. Keep Bootstrap around but avoid Bootstrap color tokens.
- **Hover behavior**: subtle gray overlay for neutral; 10% lime tint for primary actions.
- **Button styling**: NO white backgrounds. Default buttons are transparent with border and dark hover.

### Component Sources of Truth
- **Canonical Reference**: `templates/stitch/styleguide.html` - Mirror this page exactly
- **Reusable Macros**: `templates/stitch/_macros.html` - Use `badge()`, `icon_btn()`, `table()`, `toolbar()`
- **CSS Helpers**: `static/css/stitch.override.css` and `static/css/stitch.components.css`
- **Active State Logic**: `templates/base.html` - Sidebar lime highlight for Stitch routes

### Key Patterns to Follow
- Status badges: HELD (amber), FETCHED (zinc), RELEASED (green), REJECTED (red)
- Icon buttons: `.icon-btn-text` with variants `--primary`, `--danger`
- Nav tabs: Active uses lime text + 2px bottom border
- Tables: Tight spacing, subtle dividers, square status chips
- Cards: Header with toolbar, body with p-4 padding, gap-4 grids

## 🛠 Tools & MCP Configuration

### Primary Tools (Always Enabled)
- **✅ Serena MCP**: Semantic code navigation. Use for finding symbols, templates, routes, and safe edits.
- **➕ Taskmaster MCP** (optional): Bounded checklists with clear artifacts and success criteria.

### Secondary Tools (Enable on Demand)
- **🔄 GitHub MCP**: Re-enable only for repository operations. Disable by default to save context.
- **🌐 Chrome DevTools**: Enable only when debugging frontend issues.

### Working Style Guidelines
- Make small, reversible changes. Commit in logical slices with clear messages.
- When adding CSS, prefer `static/css/stitch.override.css` or `static/css/stitch.components.css`.
- When touching navigation, update `templates/base.html` endpoint checks.
- Reuse existing patterns from `/stitch` templates. If missing, add utility and use everywhere.

## 📁 File Organization

```
Email-Management-Tool/
├── templates/
│   ├── stitch/                    # Modern UI templates (source of truth)
│   │   ├── _macros.html          # Reusable components
│   │   ├── styleguide.html       # Visual reference
│   │   ├── emails-unified.html   # Email list page
│   │   ├── accounts.html         # Account management
│   │   ├── compose-email.html    # Email composition
│   │   ├── rules.html            # Moderation rules
│   │   └── watchers.html         # IMAP monitoring
│   └── base.html                 # Layout with sidebar active states
├── static/css/
│   ├── stitch.override.css       # Theme overrides
│   └── stitch.components.css     # Custom components
├── app/routes/                   # 9 Blueprint modules
└── docs/                         # Comprehensive documentation
```

## 🎯 Development Priorities

### Current Focus: Stitch UI Migration
1. **Macro Adoption**: Import and use macros in all Stitch templates
2. **Consistency**: Replace ad-hoc buttons/badges with `icon_btn()` and `badge()`
3. **Navigation**: Ensure sidebar active states work for all `/stitch` routes
4. **Polish**: Tighten spacing, fix broken links, resolve HTTP 500s

### Stitch Routes to Verify
- `/emails-unified/stitch` → `emails.emails_unified_stitch`
- `/compose/stitch` → `compose.compose_stitch`
- `/rules/stitch` → `moderation.rules_stitch`
- `/accounts/stitch` → `accounts.email_accounts_stitch`
- `/watchers/stitch` → `watchers.watchers_page_stitch`
- `/styleguide/stitch` → `styleguide.stitch_styleguide`

## 🔧 Serena MCP Usage Examples

### Navigation & Discovery
```
"Find where /styleguide/stitch is routed. If missing, show me where to add a route and which blueprint is appropriate."

"List all templates under templates/stitch/ and show me which routes render them (search in app/routes/*)."

"Show me the active-state logic in templates/base.html for sidebar items; list endpoints used for emails/compose/rules/accounts/watchers."
```

### Component & Pattern Finding
```
"Search for all uses of HELD/FETCHED/RELEASED badges; show the surrounding markup so I can normalize them."

"Show me all CSS classes that set lime color; point out duplicates."

"Find where the EMAIL VIEW page renders attachments and the API it hits. Show file + function names, then open them."
```

## 🚨 Common Issues & Quick Fixes

### Attachments HTTP 500
**Symptom**: Email detail page crashes when clicking "Attachments"
**Likely Causes**:
1. DB fetch returns `None` → unpack fails
2. File path uses stale `storage_path` or missing folder
3. `send_file` called with non-existent path

**Fix Pattern**:
```python
@emails_bp.route('/api/email/<int:id>/attachments')
def email_attachments(id):
    try:
        # Safe DB fetch with existence checks
        rows = get_attachments_for_email(id)  # returns [] if none
        data = []
        for r in rows:
            path = os.path.join(ATTACHMENTS_DIR, r['stored_name'])
            if os.path.exists(path):
                data.append({'name': r['original_name'], 'url': f'/download/{r["stored_name"]}'})
        return jsonify({'attachments': data}), 200
    except Exception as e:
        current_app.logger.exception("attachments failed")
        return jsonify({'attachments': []}), 200  # Soft failure
```

### Sidebar Active State Issues
**Check**: `templates/base.html` around line 200-250 for endpoint matching logic
**Pattern**: `request.endpoint == 'emails.emails_unified_stitch'`

### Missing Routes
**Common Missing**:
- `/email/<id>/stitch` for email detail view
- `/accounts/add` and `/accounts/import` linked from accounts page
- `/styleguide/stitch` route registration

## 💡 Best Practices

### CSS & Styling
- ✅ Use `tw-` prefixed Tailwind utilities
- ✅ Import macros: `{% from 'stitch/_macros.html' import badge, icon_btn %}`
- ✅ Consistent spacing: `tw-p-4`, `tw-gap-4`, `tw-mb-4`
- ❌ Don't add Bootstrap color classes (`btn-primary`, `text-info`)
- ❌ Don't center full pages; prefer left-aligned content
- ❌ Don't invent new colors or radii without adding tokens first

### Template Structure
```jinja
{% extends "base.html" %}
{% from 'stitch/_macros.html' import badge, icon_btn, toolbar %}
{% block title %}Page Title{% endblock %}

{% block content %}
<div id="page_id">
  <main class="tw-flex-1 tw-px-6 tw-py-4">
    <header class="tw-flex tw-justify-between tw-items-center tw-mb-4">
      <div>
        <h1 class="tw-text-2xl tw-font-bold tw-text-white">Page Title</h1>
        <p class="tw-text-sm tw-text-zinc-400 tw-mt-1">Description</p>
      </div>
      <div class="tw-flex tw-gap-2">
        {{ icon_btn('Add Item', 'add', 'primary', url_for('route.action')) }}
      </div>
    </header>
    <!-- Content -->
  </main>
</div>
{% endblock %}
```

### Commit Messages
```
feat(stitch): add macros and normalize button styling
fix(email): attachments API returns empty array on missing files
chore(stitch): tighten watchers spacing from p-6 to p-4
```

## 🎯 Success Criteria

### Visual Consistency
- [ ] No white button backgrounds anywhere in Stitch pages
- [ ] All action buttons use same shape, spacing, hover tints
- [ ] Status badges exactly match styleguide colors
- [ ] Hover overlays present on all interactive elements
- [ ] Square corners maintained (no accidental rounding)

### Functionality
- [ ] Sidebar lights up correctly for all `/stitch` routes
- [ ] "Add Account" button visible and working on accounts page
- [ ] Email attachments load without 500 errors
- [ ] All macro imports work without Jinja errors
- [ ] Navigation links go to correct destinations

### Code Quality
- [ ] Templates import and use macros consistently
- [ ] CSS changes contained in `stitch.*.css` files
- [ ] No duplicate component definitions
- [ ] All tests continue to pass

---

**Remember**: If something looks off, open `/styleguide/stitch`, import the macros, and swap ad-hoc elements for macro calls. This ensures consistency across the entire application.
