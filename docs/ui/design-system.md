# Design System (Dark Theme)

This document describes the tokens, component library, and usage patterns for the modernized UI.

## Tokens and Variables
Define all colors, spacing, shadows, and radii in static/css/main.css.

Key variables:
- Brand accent: --brand-primary: #bef264 (lime) with complementary dark text on primary CTAs
- Text: --color-text (primary), --color-text-dim (muted)
- Surfaces: --surface-base (#1a1a1a), --surface-highest (#242424)
- Borders: --border-subtle, --border-default
- Radii: --radius-sm, --radius-md, --radius-lg
- Shadows: --shadow-sm, --shadow-md, --shadow-elev-1, --shadow-elev-2

Accessibility:
- Ensure primary CTAs using lime backgrounds render with dark text (#0a0a0a) for WCAG contrast (see Buttons below)

## Include Order (Critical)
1) static/css/main.css — theme variables, layout rules, global form/tooltip styling
2) static/css/stitch.components.css — component skins: panels, tables, chips, utilities
3) Page-level overrides if absolutely necessary

Avoid resets and avoid !important unless required for legacy selectors.

## Components

### Panels
- Wrapper classes: panel-card (container), panel-header, panel-title, panel-actions, panel-body
- Use consistent spacing in header; place actions to the right in a button bar

### Buttons
- Palette: btn-secondary, btn-ghost, btn-success, btn-warning, btn-danger
- Primary CTA (lime) uses dark text. If you implement .btn-primary with lime background, set color: #0a0a0a; and provide a darker lime hover background for contrast.
- Height: 36–40px; small buttons 32–34px; consistent border radius

### Tables
- Compact dark rows with subtle borders; readable uppercase headers
- Prevent header jumping across filters by using consistent colgroup widths when needed

### Chips and Badges
- Use tag chips for statuses and watcher labels; prefer --radius-md for shape consistency

### Tooltips
- Dark theme tooltips defined in main.css; ensure data-bs-toggle="tooltip" elements match the dark shell

### Tabs (Underline Style)
- Replace filter chip-like buttons with underline tabs for mode selection
- Keep clickable area tall enough; underline animates or toggles based on active tab class
- Documented pattern to be added to templates/styleguide.html and referenced here

## Usage Notes
- Tailwind via CDN is available with the tw- prefix (preflight disabled)
- Bootstrap utilities and icons remain first-class; prefer Bootstrap grid for layout and tw- utilities sparingly where convenient
- Do not center main content; use the content-scroll shell aligned to top-left with desktop padding 28px (20px mobile)

## Live Reference
- Visit /styleguide at runtime for a live, interactive showcase of components and tokens

