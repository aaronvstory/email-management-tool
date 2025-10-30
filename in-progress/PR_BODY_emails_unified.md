feat(ui): emails unified polish — CTA contrast, tabs hooks, fixed cols, components CSS include

Summary
- Adds a dedicated components stylesheet (static/css/stitch.components.css) loaded after main.css
- Improves CTA contrast: near-black foreground text for .btn-primary and icon inheritance
- Adds minimal class hooks for tabs (tabs-bar container, tab class on buttons) without changing JS selectors/IDs
- Locks email table layout with a single <colgroup> and explicit column classes for consistent widths

Files touched (key)
- templates/base.html: include stitch.components.css after existing styles
- templates/emails_unified.html: add tabs-bar + tab classes; insert <colgroup> after <table class="table-modern email-table">
- static/css/main.css: ensure .btn-primary uses near-black text; icons inherit
- static/css/stitch.components.css: new — tabs underline, status pills, fixed table widths, truncation helpers, row actions, modal chrome

Behavioral guarantees
- No route changes, IDs, or JS handlers altered
- Purely presentational; existing event listeners continue to work

Validation
- Full test suite: 160 passed locally
- Manual QA: /emails-unified renders; API endpoints 200; no server exceptions in logs

Rollback plan
- Baseline tag v-next-ui-stitch at efafd37
- Components stylesheet is additive; removing the single <link> in base.html reverts the majority of the polish

Notes
- This sets up a shared components layer so future polish can be done via CSS without touching templates.
