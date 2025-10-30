feat(ui): compose polish — CTA contrast consistency

Summary
- Aligns compose view CTA contrast with updated design tokens
- Ensures .btn-primary foreground text is near-black for legibility on lighter accent backgrounds

Files touched (key)
- static/css/main.css: .btn-primary color override and icon inheritance (shared across app)

Behavioral guarantees
- No template or JS behavior changes

Validation
- Full test suite: 160 passed locally
- Manual QA: /compose renders; assets load; no server exceptions

Rollback plan
- Baseline tag v-next-ui-stitch at efafd37
