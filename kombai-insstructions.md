# UI Polishing Proposal and Implementation Instructions (for Kombai)

## Objective
Standardize and modernize the UI across all pages while preserving existing behavior, security, and dark-theme design system. Deliver a cohesive, maintainable, and accessible interface without altering backend logic.

## Scope
- Pages: dashboard, emails (list/detail), inbox, compose, accounts, rules, settings, watchers.
- Files to modify: `static/css/theme-dark.css`, `static/css/main.css`, templates under `templates/`.
- Do not modify: Python routes/JS behavior, CSRF hooks, SSE endpoints, encryption/security logic.

## Design System Requirements
- Color/variables (in `static/css/theme-dark.css`):
  - Use CSS variables; no hardcoded colors in templates.
  - Keep dark theme: `--primary-color: #dc2626`, `--card-bg: #1a1a1a`, gradients per STYLEGUIDE.
- Components (in `static/css/main.css`):
  - Buttons: heights sm=34px, md=42px, lg=50px; consistent padding, radius, hover states.
  - Status badges: single `.status-badge` with variants (`.held`, `.pending`, `.approved`, `.released`, `.rejected`, `.sent`, `.fetched`); 28px height; padding `0 12px`; font 12px, 700, uppercase.
  - Cards/Panels: `.card-unified` with dark gradient, subtle border, consistent padding.
  - Inputs: all inputs/selects/textarea must use `.input-modern`.
  - Spacing/typography: define scales (xs/s/m/l/xl) and use consistently.
- Remove inline styles from templates; replace with utility classes.

## Functional/Behavioral Constraints
- Must not break:
  - CSRF: keep `<meta name="csrf-token">` and hidden inputs intact.
  - Form names/ids and data-attributes used by JS.
  - Toast system in `static/js/app.js` (no browser alerts).
  - SSE endpoints (`/stream/stats`, `/api/events`).
- Do not rename routes, DOM hooks, or change form submission flows.
- Dark theme only; no light-theme toggles.

## Performance & Accessibility
- CSS: no large frameworks added; keep under reasonable size (target <200KB total CSS unminified).
- Avoid layout thrash; prefer CSS over heavy JS.
- A11y: semantic HTML, proper heading hierarchy, focus states, contrast compliant.

## Deliverables
- Updated `theme-dark.css` (variables, tokens).
- Updated `main.css` (components, utilities, removal of duplicates).
- Minimal template changes to adopt unified classes; no logic changes.
- Change summary (files touched, high-level notes).
- Optional: before/after screenshots for key pages.

## Pages Acceptance Checklist
- Global: no white flashes; `background-attachment: fixed` preserved; fonts/colors via variables only.
- Dashboard: consistent cards, buttons, badges.
- Emails list/detail: consistent badge sizes, buttons, input-modern on filters/search.
- Compose: inputs/selects/textarea use `.input-modern`; buttons sized correctly.
- Accounts/Rules/Settings/Watchers: same card/panel and spacing system across pages.
- Toasts show correctly and match dark theme.

## Workflow
- Branch: work on `kombai-ui-overhaul` (already checked out locally).
- Commit style changes incrementally; no backend file edits.
- We will review diffs and run a smoke test (launch app, verify pages) before merge.

## Files Map
- Update:
  - `static/css/theme-dark.css`
  - `static/css/main.css`
  - `templates/*.html` (minimal class replacements only)
- Keep as-is:
  - `static/js/app.js` (toasts), all `.py` files, form field names/ids, CSRF tokens.

## Examples
- Status badge usage:
  ```html
  <span class="status-badge held">HELD</span>
  <span class="status-badge pending">PENDING</span>
  ```
- Button sizes:
  ```html
  <button class="btn-modern btn-primary-modern">Primary</button>
  <button class="btn-modern btn-sm">Small</button>
  <button class="btn-modern btn-lg">Large</button>
  ```
- Inputs:
  ```html
  <input class="input-modern" type="text" />
  <select class="input-modern"></select>
  <textarea class="input-modern"></textarea>
  ```

## Non-Goals
- No JavaScript rewrites, no route renaming, no backend edits, no light theme, no design system library migration.

## Review & Sign‑off
- We will:
  - Diff all CSS/template changes for adherence to this brief and `docs/STYLEGUIDE.md`.
  - Smoke test key pages and check CSRF, forms, toasts, SSE.
  - Provide a concise before/after report and request fixes if any regressions.
