# Frontend Styling Directives (Kombai Agent Brief)

## Tech Stack Snapshot
- **Framework**: Flask + Jinja templates (`templates/*.html`).
- **Styling**: Bootstrap 5 + custom dark theme (`static/css/theme-dark.css`, `static/css/main.css`).
- **Icons**: Bootstrap Icons.
- **Behaviour**: Vanilla JS modules in `static/js/app.js` and inline per-page helpers.

## Canonical Look & Feel
Use `templates/watchers.html` as the reference. Core characteristics:
- Charcoal background gradient (`#1a1a1a ➜ #242424`) with subtle red borders (`rgba(220,38,38,0.15)`).
- Card shells `stat-card-modern` / `panel-header` with soft shadows, rounded corners, disciplined spacing.
- Button system (`btn-secondary`, `btn-ghost`, `btn-modern`) with consistent height (36–40 px), uppercase-ish labels, icon+text combos.
- Typography: white body copy, muted gray metadata (`#9ca3af`), accent greens for healthy states.

Every screen must align with those tokens; avoid the older bright-red gradients still present on several pages.

## Targeted Cleanup Checklist
Embed these tasks in each page refactor:
1. **Navigation & Header**
   - Replace legacy `.top-nav` markup with the pattern used on `/watchers`: logo/brand left, search + action buttons aligned right, consistent hover states.
   - Ensure every nav item includes an icon (e.g., add one to “Interception Test”).
   - Update footer (`templates/base.html`) so the logout bar uses panel styles (two-column flex, buttons matching `btn-ghost`).

2. **Cards / Panels**
   - Wrap sections (Dashboard stats, Diagnostics panels, Settings cards, etc.) in `stat-card-modern` or `panel-card` containers. Avoid bare `div.card`.
   - Standardize section headers via `panel-header` (title left, actions right, consistent font sizes).

3. **Forms & Inputs**
   - Apply the watchers form aesthetic: floating labels or clearly labelled inputs, 12–16 px spacing, full-width fields on small screens.
   - Rebuild the global search input (currently misaligned) as a rounded field with icon prefix, matching watchers.
   - Normalize bulk action controls (e.g., `fetchCount` selectors, “Fetch/More” buttons) so labels sit above inputs and buttons align baseline without ad-hoc margins.

4. **Tables & Lists**
   - Use a single table styling system (striped dark rows, consistent padding, sticky header if needed).
   - Add toolbars for bulk-selection actions at the top *and* bottom of long lists (e.g., Diagnostics “Pending” tab) to avoid long scrolls.

5. **Buttons & Badges**
   - Replace bespoke button classes (`btn-test`, `btn-primary`, etc.) with the shared palette: `btn-secondary`, `btn-warning`, `btn-danger`, `btn-ghost`. Keep uniform height and border radius.
   - Account action clusters (on /accounts) should use same button size; regroup into a responsive button bar.

6. **Toasts & Notifications**
   - Clean the toast component (see `templates/styleguide.html`) so padding is even, icons align left, and remove stray caret/X characters. Ensure confirm toasts share the same shell.

7. **Modals**
   - Apply consistent modal chrome (header gradient, body padding, footer buttons). `/email/<id>` and `/emails-unified` should share the same modal partial for edit/release.

8. **Style Guide**
   - Refresh `/styleguide` using the final tokens: document cards, buttons, forms, toasts, tables, and include code snippets so future work follows the same system.

## Implementation Guidelines
- Centralise colors, spacing, and shadow values in `static/css/main.css`. Introduce CSS variables (e.g., `--surface-base`, `--accent-primary`) if needed.
- Remove inline `style` attributes wherever possible; convert to classes that live in the shared stylesheet.
- Ensure responsive breakpoints (≥768 px, ≥1200 px) mirror watchers page behaviour: cards wrap into grid, controls stack vertically on small screens.
- Keep HTML semantics intact (forms, headings). Don’t rewrite back-end routes or template logic.
- After restyling, verify key flows: dashboard metrics, Held email editing, Compose page, Settings save, Diagnostics bulk discard, and toasts.

## Deliverables
- Updated templates + CSS reflecting the instructions above.
- Refreshed `templates/styleguide.html` demonstrating each standard component.
- Brief change log (per page) to accompany the PR.

## Out of Scope
- JavaScript business logic changes (unless required to reposition UI elements).
- Altering watcher functionality—it is already the design reference.
- Touching unrelated CLI scripts or back-end Python files beyond template context tweaks.

Follow this brief to produce a cohesive dark-theme dashboard that matches the quality of the `/watchers` view across the entire app.
