# Next-Agent Handoff Guide

Date: 2025-10-28
Maintainers: Team (see repo owners)
Target OS: Windows 10/11
Shell: PowerShell (pwsh)

## 1) Executive Summary
- App: Flask-based Email Management Tool with a modern dark UI.
- Status: Unified component system rolled out across most pages; Emails/Unified page needs final polish; Style Guide live at /styleguide.
- Branches:
  - Default branch: master
  - Current working branch: feat/compose-actions (stable)
  - Proposed next branch: feat/emails-unified-polish

## 2) Environment Setup (Windows PowerShell)
Use the lightweight uv workflow with a local venv:

```powershell
# From the repo root
if (-not (Test-Path .venv)) { uv venv .venv }
. .venv\Scripts\Activate.ps1
uv run python --version
```

If uv is missing, install it first (from an elevated shell if needed):

```powershell
pip install uv
```

## 3) Run the App

```powershell
# Activate venv if not already
. .venv\Scripts\Activate.ps1

# Start the app
uv run python start.py
# or
.venv\Scripts\python.exe start.py
```

- Web Dashboard: http://localhost:5000
- Live Style Guide: http://localhost:5000/styleguide

VS Code tasks (optional): see .vscode tasks listed in workspace; e.g., “UV: Run Current File”.

## 4) Design System Snapshot
- Include order (critical):
  1) static/css/main.css — theme tokens, layout, base controls, tooltips
  2) static/css/stitch.components.css — panels, tables, chips, utilities
  3) (optional) page-level overrides
- Tailwind via CDN is available with the tw- prefix; preflight is disabled. Bootstrap 5.3 + Bootstrap Icons are primary.
- Layout: content aligned top-left; 28px desktop padding (20px mobile).
- Panels: panel-card, panel-header, panel-title, panel-actions, panel-body.
- Buttons: btn-secondary, btn-ghost, btn-success, btn-warning, btn-danger. Primary (lime) CTAs must use dark text (#0a0a0a) for contrast.
- Tables: dark rows, uppercase headers, subtle hover (rgba(255,255,255,0.03)).
- Chips/Badges: use --radius-md for consistent shape; status colors use semantic vars.
- Tooltips: dark-themed globally in main.css.

References:
- docs/ui/design-system.md
- docs/STYLEGUIDE.md (historical, still useful)
- templates/styleguide.html (live examples)

## 5) Files You’ll Touch Most
- static/css/main.css — tokens, base, tooltip theme, button palette
- static/css/stitch.components.css — component visuals/utilities (add Tabs pattern here)
- templates/emails_unified.html — Emails/Unified page markup (add colgroup, tabs, action cluster)
- templates/styleguide.html — add new showcase sections (Tabs; compact status/actions)

## 6) Active Work: Emails/Unified Polish
Track in docs/ui/emails-unified-polish.md. Summary below:

- Primary CTA contrast
  - Ensure .btn-primary on lime uses color: #0a0a0a; hover deepens lime; text stays dark.
- Selector card spacing
  - Normalize vertical rhythm to 12–16px; align labels/controls; avoid ad-hoc margins.
- Filters → underline tabs
  - Implement .tabs-underline pattern with .tab and .tab-active classes (keyboard accessible, clear active state).
- Table header stability
  - Add <colgroup> with fixed widths (checkbox, subject, status, actions) to prevent jumping.
- Status/actions balance
  - Compact status badge + watcher chip; expose three primary inline actions; overflow menu for the rest.
- Style Guide
  - Add Tabs section and compact status/actions example.

Acceptance criteria are spelled out in docs/ui/emails-unified-polish.md.

## 7) Coding Guardrails
- Do not change element IDs or JS hooks without auditing dependent scripts.
- Avoid resets and avoid !important unless necessary for legacy selectors.
- Preserve include order; keep Tailwind preflight off.
- Keep HTML semantics intact; do not alter backend routes unless required.

## 8) Testing & Verification
Quick smoke run:

```powershell
# Start the app
. .venv\Scripts\Activate.ps1
uv run python start.py
```

Manual checks:
- Watchers, Rules, Settings, Interception Test, Inbox, Import Accounts render with unified chrome.
- Emails/Unified: verify CTA contrast, selector spacing, tabs visuals, no header jumps, status/actions balance.
- Style Guide at /styleguide: components render and match design system.

Extended protocol:
- See docs/UNIFIED_CSS_TESTING.md for table/hover/responsive checks.
- Optional tests (if configured locally):

```powershell
pytest -q tests
pytest -q tests/interception
```

## 9) Branching & Release Hygiene
Recommended next steps:

```powershell
# Create a stabilization tag on current HEAD
git tag -a v-next-ui-stitch -m "Stitch UI modernization baseline"

# Push branch + tag
git push origin feat/compose-actions
git push origin v-next-ui-stitch

# Cut a new feature branch for the polish work
git checkout -b feat/emails-unified-polish
```

PR checklist:
- Summarize visual changes; confirm no ID/JS breakage.
- Include before/after screenshots where helpful.
- Link to docs/ui/emails-unified-polish.md and docs/ui/design-system.md.

## 10) Paths, Logs, and Data
- Logs: logs/ (e.g., email_moderation.log)
- Data: data/ (SQLite DB, inbound_raw/ for RFC822 files)
- Backups: backups/ and database_backups/

## 11) Secrets & Env
- key.txt: Fernet key for credential encryption (git-ignored).
- .env (if present): keep out of source control.
- Never commit credentials; see README Security Note.

## 12) Known Gotchas
- Some non-nav pages may have older markup; align with panel-card system if you touch them.
- Maintain 28px desktop padding and top-left alignment—no centered shells.
- On lime CTAs, ensure text color is dark for WCAG AA.

## 13) Quick Links Index
- Live: /styleguide
- Docs index: docs/ui/README.md
- Design system: docs/ui/design-system.md
- Overview: docs/ui/modernization-overview.md
- Emails polish plan: docs/ui/emails-unified-polish.md
- Historical style guide: docs/STYLEGUIDE.md
- Unified CSS testing: docs/UNIFIED_CSS_TESTING.md

## 14) Definition of Done (for this polish phase)
- Emails/Unified passes acceptance criteria with no header jumps or contrast issues.
- Tabs pattern documented and demoed in /styleguide.
- README links to all relevant docs.
- Stabilization tag exists; new branch open for continued work.

Happy shipping! If you pick up where we left off, start at the Emails/Unified polish and Style Guide Tabs section.
