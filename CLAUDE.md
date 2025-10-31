# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Email Management Tool** is a Python Flask application for local email interception, moderation, and management. Dev-focused; runs entirely on localhost with SQLite—no cloud services, no Docker required.

**Version**: 2.9.1
**Status**: 🟢 Fully functional — SMTP proxy running; IMAP watchers using hybrid IDLE+polling strategy; core UI accessible with responsive design.
**Last Updated**: October 30, 2025

### Recent Major Updates
- ✅ **Responsive Design & CSS Consolidation** - Unified.css (145KB) with A/B toggle, sticky header fix, sidebar collapse, responsive guardrails; merged to master Oct 25 (See: [MASTER_MERGE_COMPLETE.md](MASTER_MERGE_COMPLETE.md))
- ✅ **Root Directory Cleanup** - Consolidated scattered docs, organized 19 files into `archive/2025-10-20_root_cleanup/`
- ✅ **Gmail Fixes Consolidated** - Single comprehensive reference: [docs/GMAIL_FIXES_CONSOLIDATED.md](docs/GMAIL_FIXES_CONSOLIDATED.md)
- ✅ **Implementation History** - Chronological feature history: [docs/IMPLEMENTATION_HISTORY.md](docs/IMPLEMENTATION_HISTORY.md)
- ✅ **Comprehensive Documentation** - Added USER_GUIDE, API_REFERENCE, FAQ, expanded TROUBLESHOOTING
- ✅ **UI Tooltips** - 9 tooltips across 3 templates explaining IDLE/polling, release mechanisms, rule matching
- ✅ **Test Coverage Milestone** - 138/138 tests passing, 36% coverage (was 27%), pre-commit hooks enabled
- ✅ **Hybrid IMAP Strategy** - IDLE+polling hybrid prevents timeout issues (See: [docs/HYBRID_IMAP_STRATEGY.md](docs/HYBRID_IMAP_STRATEGY.md))
- ✅ **Security Hardening** - CSRF protection, rate limiting, strong SECRET_KEY generation (See: [docs/SECURITY.md](docs/SECURITY.md))
- ✅ **Blueprint Modularization** - Routes now in app/routes/* (9 active blueprints)
- ✅ **Workspace Cleanup** - Archived 21+ redundant files, organized documentation

## At-a-Glance

| Component            | Details                                                           |
| -------------------- | ----------------------------------------------------------------- |
| **Web Dashboard**    | http://localhost:5000 (admin / admin123)                          |
| **SMTP Proxy**       | localhost:8587                                                    |
| **Database**         | SQLite (`email_manager.db`) - local only                          |
| **Encryption**       | Fernet symmetric (`key.txt`)                                      |
| **Primary Launcher** | `EmailManager.bat` (menu) or `launch.bat` (quick)                 |
| **Test Accounts**    | karlkoxwerks@stateauditgroup.com, Hostinger (mcintyre@corrinbox.com) |

⚠️ **Security Note**: Test accounts are for **development/testing only**. Never use in production.

## Quick Start

### Prerequisites
- Python 3.9+ (tested with 3.13)
- Windows environment (batch scripts)
- Email accounts with App Passwords configured

### Starting the Application

```bash
# Recommended: Professional launcher
EmailManager.bat

# Quick start
launch.bat

# Direct Python execution
python simple_app.py
```

**Access Points**:
- Web Dashboard: http://localhost:5000
- Default Login: `admin` / `admin123`

### Restarting After Port Conflicts

```bash
# Automatic cleanup and restart
python cleanup_and_start.py

# Manual cleanup
tasklist | findstr python.exe
taskkill /F /PID <pid>
python simple_app.py
```

## 🔐 Git Credentials (Automation)

**GitHub Repository**: https://github.com/aaronvstory/email-management-tool
**Username**: aaronvstory
**PAT Location**: Stored in `~/.git-credentials` (local only, not committed) or GITHUB_PAT env

**Setup for automated git push in WSL:**
```bash
# One-time setup (already configured)
echo "https://aaronvstory:<YOUR_PAT_TOKEN>@github.com" > ~/.git-credentials
git config --global credential.helper store

# Then push normally
git push origin master
```

⚠️ **Note**: PAT credentials are **already configured** in this WSL environment and stored locally in `~/.git-credentials`. Do not commit tokens to the repository.

## 🔑 Test Accounts (DO NOT MODIFY)

**CRITICAL**: These are the ONLY two accounts with confirmed working credentials.

### Account 1: Gmail - karlkoxwerks (Primary)
- **Email**: karlkoxwerks@stateauditgroup.com
- **SMTP**: smtp.hostinger.com:465 (SSL direct)
- **IMAP**: imap.hostinger.com:993 (SSL)
- **Status**: ✅ Live checks OK

### Account 2: Hostinger - Corrinbox (Secondary)
- **Email**: mcintyre@corrinbox.com
- **SMTP**: smtp.hostinger.com:465 (SSL direct)
- **IMAP**: imap.hostinger.com:993 (SSL)
- **Status**: ⚠️ Check credentials if failing

**Smart Detection**: The app auto-detects SMTP/IMAP settings from email domain.

## File Organization

```
Email-Management-Tool/
├── simple_app.py                    # Main application (~918 lines)
├── email_manager.db                 # SQLite database
├── key.txt                          # Encryption key (CRITICAL)
├── requirements.txt                 # Dependencies
├── EmailManager.bat                 # Primary launcher
├── CLAUDE.md                        # This file
├── app/
│   ├── routes/                      # 9 Blueprint modules
│   ├── services/                    # Stats, audit, IMAP workers
│   └── utils/                       # db.py, crypto.py, metrics
├── docs/                            # Comprehensive documentation
│   ├── ARCHITECTURE.md              # System architecture
│   ├── DATABASE_SCHEMA.md           # Database design
│   ├── SECURITY.md                  # Security configuration
│   ├── STYLEGUIDE.md                # UI/UX standards (MUST FOLLOW)
│   ├── HYBRID_IMAP_STRATEGY.md      # IMAP implementation
│   └── reports/                     # Analysis reports
├── tests/                           # Test suite (pytest)
├── scripts/                         # Utility scripts
├── archive/                         # Historical files
└── static/ & templates/             # Frontend assets
newly added /stich
```

## Quick Reference

### Essential Commands

```bash
# Start application
python simple_app.py

# Run tests
python -m pytest tests/ -v

# Test specific file
python -m pytest tests/test_intercept_flow.py -v

# Security validation
python -m scripts.validate_security

# Test permanent accounts
python scripts/test_permanent_accounts.py

# Health check
curl http://localhost:5000/healthz
```

### Key API Endpoints

```
# Authentication
GET  /login                          # Login page
POST /login                          # Authenticate

# Dashboard
GET  /dashboard                      # Main dashboard

# Interception
GET  /api/interception/held          # List HELD messages
POST /api/interception/release/<id>  # Release to inbox
POST /api/interception/discard/<id>  # Discard message
POST /api/email/<id>/edit            # Edit email

# Health & Monitoring
GET  /healthz                        # Health check
GET  /metrics                        # Prometheus metrics
```

## 📸 Screenshot Tooling

**Automated UI regression testing and PR documentation via Playwright**

The project includes a comprehensive screenshot capture system for:
- Multi-viewport responsive testing (desktop 1440x900, mobile 390x844)
- PR visual diffs and documentation
- Component-level element captures
- Automated CI/CD integration

### Quick Start (One Command)

```bash
# Boot app → capture screenshots → open folder
.\manage.ps1 boot-snap-open

# Or use the simplified batch file
start.bat
```

This workflow:
1. Starts the Flask app on port 5000
2. Captures full-page and element screenshots for all routes
3. Opens the `snapshots/` folder automatically

### Installation

```bash
# Install Node.js dependencies and Playwright browser
npm install
npm run snap:install
```

**First-time setup**: Copy `.snap.env.example` to `.snap.env` and configure credentials:
```ini
SNAP_BASE_URL=http://localhost:5000
SNAP_USERNAME=admin
SNAP_PASSWORD=admin123
```

### Usage Workflows

**Basic Headless Capture:**
```powershell
.\manage.ps1 snap
```

**Headful Mode (Watch Browser):**
```powershell
.\manage.ps1 snap -Headful
```

**Specific Pages Only:**
```powershell
.\manage.ps1 snap -Pages "dashboard,emails"
```

**Element-Only Screenshots:**
```powershell
# Capture specific components from dashboard
.\manage.ps1 snap -Pages "dashboard" -Elements ".page-header,.email-table"
```

**Custom Base URL:**
```powershell
.\manage.ps1 snap -BaseUrl "http://localhost:5000"
```

### CLI Flags Reference

| Flag | Description | Example |
|------|-------------|---------|
| `--base-url` | Target server URL | `--base-url http://localhost:5000` |
| `--headful` | Show browser window | `--headful` |
| `--pages` | Filter pages (comma-separated keys) | `--pages dashboard,emails` |
| `--elements` | Capture specific selectors | `--elements .page-header,.email-table` |
| `--out` | Output directory | `--out snapshots` |

### Integration with PR Workflow

**Recommended Practice:**
```bash
# 1. Make UI changes on feature branch
git checkout feat/my-ui-changes

# 2. Capture "after" screenshots
.\manage.ps1 boot-snap-open

# 3. Switch to master and capture "before" screenshots
git stash
git checkout master
.\manage.ps1 boot-snap-open
git checkout feat/my-ui-changes
git stash pop

# 4. Compare visually and include in PR description
```

**Screenshot Location:**
- Full-page: `snapshots/{timestamp}/{viewport}/{page-key}.png`
- Elements: `snapshots/{timestamp}/{viewport}/{page-key}__element__{selector}.png`

### Advanced Configuration

**Page Configuration** (`tools/snapshots/pages.json`):
```json
{
  "key": "dashboard",
  "url": "/dashboard",
  "ready": "#dashboard-page",
  "elements": [".page-header", ".email-table", ".stats-grid"]
}
```

**Authentication State**: Stored in `tools/snapshots/state.json` (gitignored)
- Automatically logs in once and reuses session
- Regenerate: `npm run snap:update-state`

### Troubleshooting

**Port already in use:**
```powershell
# manage.ps1 automatically waits for port 5000
# If stuck, manually kill processes:
Get-Process python | Where-Object {$_.Path -like "*Email-Management-Tool*"} | Stop-Process -Force
```

**Authentication failing:**
- Verify `.snap.env` credentials match your test account
- Regenerate auth state: `npm run snap:update-state`

**Screenshots missing:**
- Check `ready` selector exists in target page
- Run in headful mode to debug: `.\manage.ps1 snap -Headful`

**Full Documentation**: `tools/snapshots/README.md` (615 lines)

## AI-Assisted Development
Macros you can use everywhere

### `templates/stitch/_macros.html`

```jinja
{# Reusable components for Stitch pages #}
{% macro badge(kind) -%}
  {%- set map = {
    'HELD':       'tw-bg-amber-500/15 tw-text-amber-400',
    'FETCHED':    'tw-bg-zinc-700 tw-text-zinc-400',
    'RELEASED':   'tw-bg-green-500/15 tw-text-green-400',
    'REJECTED':   'tw-bg-red-500/15 tw-text-red-400',
    'PENDING':    'tw-bg-zinc-700 tw-text-zinc-300',
    'ERROR':      'tw-bg-red-500/15 tw-text-red-400'
  } -%}
  <span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] {{ map.get(kind|upper, 'tw-bg-zinc-700 tw-text-zinc-300') }}">{{ kind|upper }}</span>
{%- endmacro %}

{% macro icon_btn(label='', icon='more_horiz', variant='neutral', href=None) -%}
  {%- set v = {
    'neutral': '',
    'primary': 'icon-btn--primary',
    'danger':  'icon-btn--danger'
  }[variant] -%}
  {%- if href -%}
    <a href="{{ href }}" class="icon-btn-text {{ v }}">
      <span class="material-symbols-outlined tw-!text-base">{{ icon }}</span> {{ label }}
    </a>
  {%- else -%}
    <button class="icon-btn-text {{ v }}">
      <span class="material-symbols-outlined tw-!text-base">{{ icon }}</span> {{ label }}
    </button>
  {%- endif -%}
{%- endmacro %}

{# Simple table shell; pass safe HTML rows or render per-row outside #}
{% macro table(headings=[], rows_html='') -%}
  <div class="tw-bg-background tw-border tw-border-border">
    <div class="tw-overflow-x-auto">
      <table class="tw-w-full tw-text-sm tw-text-left">
        <thead class="tw-text-zinc-400 tw-border-b tw-border-border">
          <tr>
            {%- for h in headings %}
              <th class="tw-px-4 tw-py-2">{{ h }}</th>
            {%- endfor %}
          </tr>
        </thead>
        <tbody class="tw-divide-y tw-divide-[rgba(255,255,255,.06)]">
          {{ rows_html|safe }}
        </tbody>
      </table>
    </div>
  </div>
{%- endmacro %}

{# Toolbar with right-aligned actions #}
{% macro toolbar(title='', actions=[]) -%}
  <div class="tw-p-4 tw-border-b tw-border-border tw-flex tw-justify-between tw-items-center">
    <h3 class="tw-text-zinc-200 tw-font-semibold">{{ title }}</h3>
    <div class="tw-flex tw-gap-2">
      {%- for a in actions %}
        {{ icon_btn(a.label, a.icon, a.variant, a.href) }}
      {%- endfor %}
    </div>
  </div>
{%- endmacro %}
```

```jinja
{% from 'stitch/_macros.html' import badge, icon_btn, table, toolbar %}
```

 Wire the macros into pages

### Emails (list rows) — `templates/stitch/emails-unified.html`

At the top:


Use in a row:

```jinja
<td class="tw-px-4 tw-py-3">{{ badge(email.status) }}</td>
<td class="tw-px-4 tw-py-3">
  <div class="tw-flex tw-justify-end tw-gap-2">
    {{ icon_btn('Attachments', 'download', 'neutral', url_for('emails.attachments', id=email.id)) }}
    {{ icon_btn('Release', 'check_circle', 'primary', url_for('interception.release', id=email.id)) }}
    {{ icon_btn('Discard', 'delete', 'danger', url_for('interception.discard', id=email.id)) }}
  </div>
</td>
```
### Rules — `templates/stitch/rules.html`

```jinja
{% from 'stitch/_macros.html' import badge, icon_btn, table, toolbar %}

{{ toolbar('Rules',
  actions=[
    {'label': 'New Rule', 'icon': 'add', 'variant': 'primary', 'href': url_for('moderation.new_rule')},
    {'label': 'Refresh',  'icon': 'refresh', 'variant': 'neutral', 'href': url_for('moderation.rules_stitch')}
  ]
)}}
```


### Active MCP Servers
This project uses Model Context Protocol (MCP) servers for enhanced development capabilities:

**Primary Tools**:
- **Serena** - Semantic code intelligence for Python
  - Symbol-aware code navigation and editing
  - Safe refactoring with dependency tracking
  - Dashboard: http://127.0.0.1:24282/dashboard/index.html
  - Use for: Finding functions/classes, analyzing imports, project-wide changes
- **Desktop Commander** - File system and process management
  - File operations, directory traversal, search capabilities
  - Process management and system commands
  - Use for: File I/O, bulk operations, system diagnostics
- **Sequential Thinking** - Complex multi-step analysis and planning

- chrome-devtools (browser automation - enable manually when needed)

### `/sp` Command (SuperPower Orchestration)
Primary command for intelligent task orchestration across all MCP servers.

**Usage**:
```bash
/sp [task description]
```

**Examples**:
```bash
/sp analyze the SMTP proxy authentication flow
/sp refactor IMAP watcher to use better error handling
/sp add comprehensive logging to interception.py
/sp find all SQL queries and check for injection risks
```

**Auto-Detection**:
- Code analysis → Activates Serena MCP (semantic understanding)
- Research tasks → Activates Exa/Perplexity (web search)
- File operations → Uses Desktop Commander (file system)
- Library questions → Uses Context7 (documentation lookup)

**Features**:
- Automatically spawns expert sub-agents for complex tasks
- Coordinates between multiple MCP servers intelligently
- Saves research findings to `.claude/research/` for reuse
- 87% token reduction through intelligent caching

## Development Guidelines

### State Management
- **Database Access**: Always use `app.utils.db.get_db()` context manager for thread-safe connections
- **Row Factory**: Enables dict-like access to query results (`row['column']` instead of `row[0]`)
- **Thread Safety**: SQLite WAL mode + busy_timeout handles concurrent access from multiple threads
- **Caching**: Stats endpoints use TTL-based caching (2-5 seconds) to reduce database load


# CLAUDE.md

## Project
Email Management Tool — Flask + Jinja + SQLite. Runs locally. Dark UI with lime accents (#bef264), square corners, Tailwind (prefix `tw-`, preflight disabled), plus a few custom CSS files.

## Absolute UI rules
- Primary accent = lime #bef264. No blues. No bootstrap theme colors.
- Square corners (no rounding unless explicitly set in a component).
- Dark surfaces: base #18181b, surface #27272a, borders rgba(255,255,255,.12).
- Avoid introducing Bootstrap’s default colors/variables into new code.
- Prefer utility classes with `tw-` prefix + small scoped component helpers in `static/css/stitch.*.css`.

## Tools (MCP) to favor
- ✅ **Serena** (semantic code nav): use it for finding symbols, related templates, shared helpers, and safe edits.
- ➕ (optional later) **Taskmaster**: run bounded checklists with clear artifacts.
- 🚫 Disable/avoid: github MCP, chrome-devtools MCP (re-enable only when needed) to keep context small.

## Working style
- Make small, reversible changes. Commit in logical slices with clear messages.
- When adding CSS, prefer `static/css/stitch.override.css` or `static/css/stitch.components.css`.
- When touching navigation active states, update `templates/base.html` endpoint checks.
- Reuse existing patterns from `/stitch` templates. If missing, add a tiny utility and use it everywhere.

## What “good” looks like
- Links: subtle gray hover overlay; lime on “primary” links.
- Buttons: no white backgrounds; themed hover tints; icon + label aligned.
- Badges: compact, uppercase, square, dark chip background.
- Tables: tight spacing, zebra optional, borders subtle.
- Sidebar: lime active state with 3px left border, 10% lime tint background.

## Serena usage templates
- “Find where the EMAIL VIEW page renders attachments and the API it hits. Show file + function names, then open them.”
- “List all templates under templates/stitch/* and the routes that render them.”
- “Show me all CSS classes that set lime color; point out duplicates.”

## Don’ts
- Don’t add bootstrap “primary/secondary/etc.” utility classes.
- Don’t re-center full pages; prefer left-aligned content and conservative spacing.
- Don’t invent new colors or radii unless we add tokens first.


#  The “Ultimate Stitch Styleguide” (spec + skeleton)

Use this as the single source of truth. It names tokens, utilities, and components we already rely on in your screenshots + templates, and it’s small enough for Claude to keep in context.

## Design tokens (reference)

* Colors

  * `--bg: #18181b`, `--surface: #27272a`, `--border: rgba(255,255,255,.12)`
  * `--text: #e5e7eb`, `--muted: #9ca3af`
  * `--primary: #bef264` (lime), hover `#a3d154`
  * semantic (use sparingly): `--success: #22c55e`, `--warning: #f59e0b`, `--danger: #ef4444`
* Radii: `0px` default. Use `4px` only on small chips if needed.
* Shadows: very light or none (we’re in dark UI).
* Spacing: prefer `tw-p-4`, `tw-gap-4` over 6/8 unless it truly breathes better.

## Global utilities (CSS you already started)

* `.icon-btn-text` (+ `--primary`, `--danger`) for small action buttons
* link hover overlay (gray) and lime hover for “primary links”
* tables and chips use dark surfaces, square edges

## Components to standardize

1. **Primary button**

```html
<button class="tw-inline-flex tw-items-center tw-gap-2 tw-font-bold tw-text-zinc-900 tw-bg-primary tw-border tw-border-[#bef264] tw-px-4 tw-py-2 hover:tw-bg-[#a3d154]">
  <span class="material-symbols-outlined tw-!text-base">add</span> Add Account
</button>
```

2. **Ghost action (icon + text)**

```html
<button class="icon-btn-text icon-btn--primary">
  <span class="material-symbols-outlined tw-!text-base">edit</span> Edit
</button>
<button class="icon-btn-text icon-btn--danger">
  <span class="material-symbols-outlined tw-!text-base">delete</span> Delete
</button>
```

3. **Nav tabs (All / Held / Released / Rejected)**

```html
<nav class="tw-flex tw-items-center tw-gap-3">
  <a class="tw-text-sm tw-font-semibold tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60 tw-rounded-[0] tw-transition">All <span class="tw-text-zinc-500 tw-ml-1">412</span></a>
  <a class="tw-text-sm tw-font-semibold tw-text-primary tw-px-2 tw-py-1 tw-border-b-[2px] tw-border-primary">Held <span class="tw-text-zinc-500 tw-ml-1">337</span></a>
  <a class="tw-text-sm tw-font-semibold tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">Released <span class="tw-text-zinc-500 tw-ml-1">75</span></a>
  <a class="tw-text-sm tw-font-semibold tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">Rejected <span class="tw-text-zinc-500 tw-ml-1">0</span></a>
</nav>
```

4. **Status badges (HELD / FETCHED / RELEASED)**

```html
<span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-zinc-700 tw-text-zinc-400">FETCHED</span>
<span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-amber-500/15 tw-text-amber-400">HELD</span>
<span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-green-500/15 tw-text-green-400">RELEASED</span>
```

5. **Sidebar active state** (already implemented)

* lime text, 10% lime background, 3px lime left border, tighter left padding on the active item

6. **Cards & grids**

* reduce padding from `tw-p-6` → `tw-p-4` unless content needs more room
* gaps `tw-gap-4` default

> the watchers skeleton you uploaded is a good structure reference for the blocks and headers

### File to create/update for the styleguide

* `templates/styleguide/stitch.html` with sections:

  1. Colors & tokens (chips showing each token)
  2. Typography (sizes actually used)
  3. Buttons (primary, ghost/icon, destructive)
  4. Nav tabs (All/Held/Released/Rejected)
  5. Badges (HELD/FETCHED/RELEASED)
  6. Forms (inputs, selects, switches)
  7. Tables (header, row, actions)
  8. Cards/panels (header, toolbar)
  9. Sidebar active example (inline demo)
  10. Examples: “Emails row” and “Accounts card” patterns

---

“AI-Assisted Development”)

```md
## AI Assistant Configuration (Frontend focus)

**Primary MCP:** Serena (semantic code intelligence for Python + Jinja)
- Use Serena for: symbol lookups, finding template usages, safe refactors, and locating routes/endpoints.
- Prefer Serena over generic regex search.

**Disable by default to save context:** github, chrome-devtools
- Re-enable only when you need them for a very specific action.

**Design guardrails (MANDATORY):**
- Dark theme only, square corners.
- Accent lime: `#bef264`, hover: `#a3d154`.
- Tailwind with `prefix: 'tw-'`, `preflight: false`.
- No Bootstrap blues, no rounded badges, no glowing shadows.
- Reuse macros: `templates/stitch/_macros.html` (`badge`, `icon_btn`, `table`, `toolbar`).
- Reuse helpers: `static/css/stitch.components.css`, `static/css/stitch.override.css`.

**Canonical reference for visuals:** `templates/styleguide/stitch.html`
- If in doubt, mirror that page exactly.
- Do not invent new colors or sizes.

**Execution checklist for any UI change:**
1. Check `base.html` for sidebar active state.
2. Import macros at top of template and replace ad-hoc buttons/badges.
3. Verify link hover overlays and no white backgrounds.
4. Validate page at runtime, then add tests if endpoint changed.

**Performance & context hygiene:**
- Keep MCP count minimal; prefer Serena.
- Summarize diffs in commit messages; avoid long chat dumps.
CSS helpers (if not already present)

Append to `static/css/stitch.components.css` (you already started this file; these are safe additions):
Styleguide route

If you need it:

```python
# app/routes/styleguide.py
from flask import Blueprint, render_template
from flask_login import login_required

styleguide_bp = Blueprint('styleguide', __name__)

@styleguide_bp.route('/styleguide/stitch')
@login_required
def stitch_styleguide():
    return render_template('styleguide/stitch.html')
```

Register in your app factory / main app init:

```python
from app.routes.styleguide import styleguide_bp
app.register_blueprint(styleguide_bp)
```
```css
/* === Icon Button Variants (Text + Icon) === */
button.icon-btn-text,
a.icon-btn-text {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.5rem;
  font-weight: 500;
  font-size: 0.875rem;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 4px;
  transition: background-color 0.15s ease, color 0.15s ease;
}
button.icon-btn-text:hover,
a.icon-btn-text:hover { background: rgba(39,39,42,0.6); }

button.icon-btn-text.icon-btn--danger:hover,
a.icon-btn-text.icon-btn--danger:hover {
  background: rgba(239,68,68,0.1);
  color: #f87171;
}

button.icon-btn-text.icon-btn--primary:hover,
a.icon-btn-text.icon-btn--primary:hover {
  background: rgba(190,242,100,0.1);
  color: #a3d154;
}
```
### Database Operations
Always use `row_factory` for dict-like access:












```python
from app.utils.db import get_db

with get_db() as conn:
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM email_messages WHERE status=?", ('PENDING',)).fetchall()
    for row in rows:
        print(row['subject'])  # Dict access, not row[2]
```

### Blueprint Structure
Routes are organized in `app/routes/`:
- `auth.py` - Authentication
- `dashboard.py` - Dashboard views
- `stats.py` - Statistics APIs
- `moderation.py` - Rule management
- `interception.py` - Email hold/release/edit
- `emails.py` - Email CRUD
- `accounts.py` - Account management
- `inbox.py` - Inbox viewer
- `compose.py` - Email composition

## Current Capabilities

✅ Full email interception (SMTP + IMAP)
✅ Multi-account management with smart detection
✅ Email editing before approval
✅ Dashboard with live stats
✅ Risk scoring and filtering
✅ Complete audit trail
✅ Attachment handling
✅ Real-time monitoring
✅ Encrypted credential storage
✅ **Modern toast notification system** - No more browser alerts!
✅ **Production-ready security** - CSRF, rate limiting, strong SECRET_KEY

## Known Limitations

✅ **Test Coverage**: 36% code coverage, 138/138 tests passing (target: 50%+)
⚠️ **SMTP Proxy**: Must be running (check /api/smtp-health)
⚠️ **Port Conflicts**: May need cleanup_and_start.py if port 8587 is in use

## Troubleshooting Quick Reference

**Gmail Authentication Failed**
→ Use App Password (with spaces), verify 2FA enabled

**Port Already in Use**
→ `python cleanup_and_start.py` or manually kill python.exe processes

**Database Schema Mismatch**
→ Check docs/DATABASE_SCHEMA.md for migration scripts

**UI Styling Issues**
→ Consult docs/STYLEGUIDE.md for proper patterns

## Detailed Documentation

For deeper technical information, see:

**Getting Started**:
- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** - Complete step-by-step workflows and walkthroughs
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - REST API documentation with cURL examples
- **[docs/FAQ.md](docs/FAQ.md)** - Frequently asked questions
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues, gotchas, and solutions

**Architecture & Design**:
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design
- **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - Database design and indices
- **[docs/TECHNICAL_DEEP_DIVE.md](docs/TECHNICAL_DEEP_DIVE.md)** - Architecture deep dive

**Development & Deployment**:
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development workflow
- **[docs/TESTING.md](docs/TESTING.md)** - Testing strategy
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide

**Configuration & Security**:
- **[docs/SECURITY.md](docs/SECURITY.md)** - Security configuration and validation
- **[docs/STYLEGUIDE.md](docs/STYLEGUIDE.md)** - UI/UX standards (MANDATORY)
- **[docs/HYBRID_IMAP_STRATEGY.md](docs/HYBRID_IMAP_STRATEGY.md)** - IMAP implementation

**Implementation & History**:
- **[docs/GMAIL_FIXES_CONSOLIDATED.md](docs/GMAIL_FIXES_CONSOLIDATED.md)** - Complete Gmail duplicate fix documentation (v1-v4 evolution, protocol fixes, hardening)
- **[docs/IMPLEMENTATION_HISTORY.md](docs/IMPLEMENTATION_HISTORY.md)** - Chronological feature implementation history (Oct 18-19, 2025)
- **[docs/SMOKE_TEST_GUIDE.md](docs/SMOKE_TEST_GUIDE.md)** - End-to-end Gmail release validation guide
- **[docs/reports/CODEBASE_ANALYSIS.md](docs/reports/CODEBASE_ANALYSIS.md)** - Comprehensive architecture and implementation review (2390 lines)
- **[archive/2025-10-20_root_cleanup/MANIFEST.md](archive/2025-10-20_root_cleanup/MANIFEST.md)** - Root directory cleanup documentation

---

**Remember**: This application IS working. If it's not:
1. Check `python simple_app.py` is running
2. Access http://localhost:5000
3. Verify accounts configured with `python scripts/verify_accounts.py`
4. Check `logs/app.log` for errors
5. Test connections with `python scripts/test_permanent_accounts.py`
