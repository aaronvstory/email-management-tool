Got it — and nice progress. Here’s a clean “starter brief” you can paste at the top of any new chat with me so I’m loaded with the right context and standards from the jump.

# Starter Prompt for New Sessions

**Project:** Email Manager (Flask + Jinja + vanilla JS)
**Repo:** connected via GitHub connector
**Current default branch:** `feat/emails-unified-polish` (verify first)
**Scope right now:** finish polishing UI across pages. Backend logic stays untouched unless a UI hook needs it.

## Quick context

* Templates live in `templates/*.html`.
* CSS lives in `static/css/`. Use page-scoped patch files over global edits:

  * `static/css/patch.dashboard-emails.css` for Dashboard + Emails.
  * Prefer scoped selectors like `#dashboard-page …` or `#emails-unified-page …`.
* JS lives in `static/js/app.js`. Use existing helpers under `window.MailOps`. No new libs.
* Tables use `table-layout: fixed` with `<colgroup>`. Don’t remove it.
* Actions on rows:

  * HELD: Release, Edit, Reject + kebab for secondary actions.
  * Released/Rejected: View only or kebab for audit-type stuff.
* Avoid `!important` unless narrowly scoped and there’s a clear reason.

## What to do first

1. Confirm you’re looking at the right branch and files.

   * Run a connector search for `templates/<target>.html` and `static/css/patch.dashboard-emails.css`.
   * If default branch isn’t the feature branch, tell me and I’ll switch it.
2. Read the page template and the patch CSS section for that page.
3. Propose a short, numbered plan. Then implement in small patches.

## House style and UX rules

* Keep typography readable on dark backgrounds. Don’t use low-contrast “muted” grays.
* Reuse chip-style buttons for compact actions. Height ~28px. Icon size ~14px.
* Align action clusters to the right inside a fixed-width `col-actions`.
* Checkbox column must never ellipsize. No hidden select-all.
* Time shows two lines: line 1 time, line 2 date. Subject shows two-line clamp.
* Kebab menu opens next to its trigger. No jumping to the corner.

## Definition of done (per change)

* Visual: spacing, alignment, and truncation look right at 1440, 1024, 768.
* Functional: select-all works, row actions trigger the same handlers as before.
* No new console errors. No layout shifts when toggling tabs or pagination.
* Only modified the intended templates, `patch.*.css`, and `app.js` helpers.
* Leave a concise change note in the reply: files touched, what changed, and why.

## Output format I want

* Short plan → code patches → exactly where to paste them.
* Keep changes scoped. No broad rewrites.
* If something is ambiguous, make a best call and note your assumption.

## Do not

* Don’t add frameworks or new global CSS files.
* Don’t move backend routes or data models.
* Don’t restyle unrelated pages in the same patch.

---

### First target after loading context

Tell me which page you’ll fix next and why. Likely candidates:

* `templates/watchers.html` needs a pass.
* `templates/styleguide.html` should be the single source of truth for tokens and components.

If you need me to switch the repo’s default branch again for tool access, say so and I’ll do it.
