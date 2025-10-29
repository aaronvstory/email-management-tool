# Style Guide Usage

The live UI Style Guide is available at runtime and serves as the canonical reference for tokens and components.

- Route: GET /styleguide
- Template source: templates/styleguide.html

## What’s Inside
- Panels and cards (panel-card/header/title/actions/body)
- Buttons (palette, sizing, hover states, button bars)
- Tooltips (dark theme)
- Selector card pattern
- Status banner and chips
- Compact tables
- Toasts and notifications
- Tabs (underline style) — to be added alongside Emails/Unified polish

## How to Extend
1) Add the new component example to templates/styleguide.html under the appropriate section
2) Ensure styles live in static/css/stitch.components.css (structure) and static/css/main.css (tokens)
3) Keep examples small and focused, with minimal inline styles
4) Verify accessibility (contrast, focus outlines, keyboard navigation)

## Related Docs
- Design system and include order: ./design-system.md
- Emails/Unified polish plan: ./emails-unified-polish.md
- Global historical style guide: ../STYLEGUIDE.md

