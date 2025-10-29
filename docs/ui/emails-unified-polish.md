# Emails/Unified — Visual Polish Plan

Status: Planned and in-progress
Updated: 2025-10-28

## Issues to Address
1) Primary CTA contrast
- Lime primary button must use dark text for accessibility
- Hover state should deepen lime tone, text stays dark

2) Selector card spacing
- Tighten vertical rhythm: label → control → helper aligned to 12–16px increments
- Normalize baseline alignment across selector, search, and action cluster

3) Filters as underline tabs
- Replace chip-like filter buttons with underline-style tabs matching dashboard aesthetics
- Tabs must be keyboard-focusable and clearly indicate active state

4) Table header stability
- Prevent header/column jumping when switching filters
- Introduce a <colgroup> with fixed widths for critical columns (checkbox, subject, status, actions)

5) Status + actions cell balance
- Combine a compact status badge with a watcher chip
- Expose three primary inline actions; tuck the rest into an overflow (kebab) menu

6) Style Guide updates
- Add Tabs pattern and the compact status/actions example to /styleguide

## Acceptance Criteria
- No layout shifts when toggling filters or pagination
- Primary CTA passes WCAG AA contrast with dark text
- Selector area aligns visually with consistent spacing
- Tabs look and behave consistently across viewport widths
- Actions cluster does not wrap awkwardly at common breakpoints

## Implementation Hints
- Buttons: ensure .btn-primary in main.css uses color: #0a0a0a on lime background
- Tabs: implement a .tabs-underline pattern in stitch.components.css with .tab and .tab-active classes
- Table: add a <colgroup> to templates/emails_unified.html and fix widths for first/last columns; distribute remaining width sensibly
- Actions: create a small utility .action-btn for compact icon+text buttons; use a dropdown for overflow

## Test Checklist
- Toggle between tabs rapidly; confirm header remains stable
- Resize to 1280px, 1200px, 1024px, 900px; confirm actions stay usable
- Run through bulk selection; sticky toolbar appears and matches panel chrome
- Verify tooltips maintain contrast on dark theme

