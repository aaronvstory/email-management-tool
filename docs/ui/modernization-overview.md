# UI Modernization: Overview and Scope

Date: 2025-10-28
Status: In progress (majority complete; remaining polish tracked here)

## Goals
- Modern, minimal dark theme with left/top-aligned content and desktop padding of 28px (20px mobile)
- Unified component system (panels, buttons, tables, chips, tooltips) with consistent spacing and elevations
- No breaking changes to IDs or JavaScript behavior; changes are purely visual and structural
- Comprehensive Style Guide to keep all future work consistent

## Tech Stack and Conventions
- Flask + Jinja templates (templates/*.html)
- Bootstrap 5.3 + Bootstrap Icons
- Tailwind via CDN (scoped to the tw- prefix, preflight disabled)
- CSS include order (critical):
  1) static/css/main.css (theme variables, base, layout)
  2) static/css/stitch.components.css (component skins/utilities)
  3) optional page-level CSS patches if required
- No global resets; avoid !important unless necessary for legacy interop

## What’s Been Modernized
- Unified panel chrome: panel-card, panel-header, panel-title, panel-actions, panel-body
- Button palette and sizing: btn-secondary, btn-ghost, success/warning/danger, consistent heights
- Table helpers: compact dark rows, stable padding, readable headers
- Chips and statuses: tag chips, watcher chips, soft badges
- Tooltips: dark theme with accessible contrast
- Layout rules: content scroll area pinned left/top (not centered), padding 28px desktop/20px mobile

## Pages Converted to the New Pattern
- Watchers
- Rules
- Settings
- Interception Test Dashboard
- Inbox
- Import Accounts
- Emails — Unified (functional under the new chrome; final polish tracked below)

## Remaining Work (Tracked in emails-unified-polish.md)
- Primary lime call-to-action requires dark text for WCAG contrast
- Selector card spacing rhythm needs tightening
- Replace chip filters with underline-style tabs (match dashboard aesthetic)
- Stabilize table header/columns (prevent jumping across filters)
- Rebalance status/actions cell: compact status + watcher chip + 3 inline actions + overflow menu
- Style Guide additions: Tabs pattern; compact status/actions example

## Non-Goals
- No changes to back-end routes or business logic unless required to reposition UI elements
- No Tailwind preflight; keep bootstrap utility compatibility intact

## How to Verify
- Start the app and navigate major pages; check for consistent panel chrome, spacing, and button sizing
- Visit /styleguide for live components and visual tokens
- Review docs/ui/design-system.md for how to apply components correctly

