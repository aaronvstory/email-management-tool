You’re continuing the UI/UX modernization of the Email-Management-Tool repo (same workspace as before). Key context:

  - The design system lives in static/css/main.css with a large CSS-variable token block (surfaces, borders, brand, semantic colors, spacing, radii, shadows, gradients). All
  components should use these tokens—no hard-coded colours or inline styles.
  - templates/watchers.html is the canonical visual reference; every screen should inherit its “panel + stat-card-modern” aesthetic, button sizes, gradients, and toast
  styling.
  - templates/accounts.html has already been refactored accordingly (panel header, stat-card layout, helper classes, zero inline styles). Use it as the working example of the
  target markup.
  - static/css/main.css now contains helper classes for accounts: .account-meta, .account-row, .account-error, etc. Build similar helpers for any new layouts so templates
  remain class-driven.

  The remaining work:
  1. Roll the token-driven refactor across the dashboard templates that still use legacy styling, especially:
     - templates/dashboard_unified.html (tabbed Dashboard + Accounts + Diagnostics views)
     - templates/dashboard_interception.html
     - templates/dashboard_rules.html and templates/rules.html (deduplicate styling and behaviour)
     - templates/dashboard_accounts.html (if present) plus any partials referenced in the dashboard tabs
     - templates/styleguide.html (update to document the new token system and components)
     - templates/compose.html and templates/settings.html (convert headers, cards, forms, buttons, modals to the shared patterns)
  2. Eliminate duplicated markup between the left-nav pages (/accounts, /rules, etc.) and the dashboard tabs (/dashboard/accounts, /dashboard/rules). Prefer shared partials or
  macros so both routes render identical components.
  3. Ensure the toast/notification components, bulk-action toolbars, and modals all use the shared CSS (no inline style, consistent sizing/spacing).
  4. After each template refactor, run a quick search to confirm no `style="` attributes remain and that new helpers are defined in main.css using tokens.
  5. Keep the codebase Python-compatible: update any Flask routes or blueprint references necessary when introducing shared partials or moving templates.
  6. Provide a short change summary at the end, noting files touched and any partials/macros you introduced.

  Please begin by auditing the dashboard-related templates to map out overlap, then proceed with the refactor + deduplication sequence described above. Let me know once the
  rollout is complete or if you hit any blocking conflicts.
