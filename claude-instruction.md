Attachments HTTP 500: quick triage note for Claude

* Repro: open `/email/<id>` then click “Attachments” → 500
* Likely causes:

  1. DB fetch for attachments returns `None` → unpack used without guard
  2. File path built from stale `storage_path` or missing folder
  3. Response tries to `send_file` with a non-existing path
* Fix steps:

  * Add safe-guards: if no attachments, return empty `[]` and 200
  * Verify path join uses `os.path.join(ATTACHMENTS_DIR, stored_name)` and `os.path.exists`
  * Wrap send in try/except; on FileNotFoundError, log and return `{ attachments: [] }`
  * Add a tiny JSON endpoint test that asserts 200 with empty list when none found

Example API shape (adjust to your code):

```python
@emails_bp.route('/api/email/<int:id>/attachments')
@login_required
def email_attachments(id):
    try:
        conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("SELECT original_name, stored_name FROM email_attachments WHERE email_id=?", (id,)).fetchall()
        data = []
        for r in rows:
            p = os.path.join(ATTACHMENTS_DIR, r['stored_name'])
            if os.path.exists(p):
                data.append({'name': r['original_name'], 'url': url_for('emails.download_attachment', name=r['stored_name'])})
        return jsonify({'attachments': data}), 200
    except Exception as e:
        current_app.logger.exception("attachments failed")
        return jsonify({'attachments': []}), 200
    finally:
        conn.close()
```




# 3) One-hour unattended task (for Claude/Taskmaster)

> copy-paste this **as the single task** to Claude (with Serena enabled; github/chrome MCP disabled):

**Title:** Stitch Styleguide + UI polish pass (bounded 60 min)

**Inputs:**

* `templates/base.html`, `templates/stitch/*.html`
* `static/css/stitch.override.css`, `static/css/stitch.components.css`
* This spec in CLAUDE.md (tokens, components, patterns)

**Goals (in order):**

1. **Styleguide page**

   * Create `templates/styleguide/stitch.html` with sections listed above.
   * Each section must render example markup that uses existing CSS and `tw-` utilities (no new colors).
   * Add route if missing: `/styleguide/stitch`.

2. **Compose polish**

   * Confirm compose page is left-aligned (not centered).
   * Ensure “Back to Emails” link works and uses lime hover tint.

3. **Accounts page**

   * Ensure a visible **Add Account** primary button (lime) exists.
   * Make card action buttons use `.icon-btn-text` pattern consistently.

4. **Emails list**

   * Use the status badges spec for HELD/FETCHED/RELEASED.
   * Make row action buttons consistent with `.icon-btn-text`.

5. **Watchers spacing**

   * Keep `tw-p-4` and `tw-gap-4` defaults; ensure headers and toolbars are snug.

6. **Sidebar active states**

   * Confirm stitch routes light up the proper nav item (emails/compose/rules/accounts/watchers).

**Deliverables:**

* New file: `templates/styleguide/stitch.html`
* Updated files touched above
* Commit messages (slice by slice):

  * `feat(styleguide): add stitch styleguide with components + tokens`
  * `fix(stitch): compose back link + left align layout`
  * `feat(stitch): accounts add-account button + normalized card actions`
  * `fix(stitch): emails row actions + status badges`
  * `chore(stitch): tighten watchers spacing`

**Guardrails:**

* No bootstrap color utilities or rounded corners by default.
* Keep CSS changes inside `stitch.override.css` or `stitch.components.css`.
* Prefer minimal new CSS; compose with `tw-` utilities first.
* Run tests if available; don’t modify backend logic.

**Logging (short):**

* Before each change: “Open files: …”
* After each change: “Diff summary: …”
* End: “Touched files + commit hashes”

**Stop conditions:**

* 60 minutes elapsed OR all goals complete.
* If a template/route is missing critical data, create a stub that renders safely without backend calls.

---

# 4) Serena MCP prompts (ready to paste)

* “Find where `/styleguide/stitch` is routed. If missing, show me where to add a route and which blueprint is appropriate.”
* “List all templates under `templates/stitch/` and show me which routes render them (search in `app/routes/*`).”
* “Search for all uses of HELD/FETCHED/RELEASED badges; show the surrounding markup so I can normalize them.”
* “Show me the active-state logic in `templates/base.html` for the sidebar items; list endpoints used for emails/compose/rules/accounts/watchers.”

---

# 5) Attachments HTTP 500 — quick triage recipe (handy while Claude runs)

If you want to hand Claude a follow-up task after the styleguide:

**Title:** Fix attachments 500 in email view

**Steps:**

1. Serena: “Find all routes that serve attachments or message detail: search in `app/routes/emails.py`, `app/routes/interception.py`, and APIs under `/api/email/*`.”
2. Open the failing route + any helper in `app/services/*`; check for:

   * path joins, file existence, wrong `mimetype`, db row missing
   * exceptions hidden by a broad `except`
3. Reproduce in logs: check `logs/app.log`. Add a temporary `app.logger.exception('attachments failed')` around the handler.
4. Fix obvious errors (e.g., wrong column name, missing join, invalid id parsing).
5. Return 404/400 gracefully on missing files; never 500 on user error.
6. Add a tiny “Attachments” panel to the email view stitch page that shows empty state cleanly.

**Deliverables:** commit `fix(email): attachments handler returns file or 404; stitch UI panel`

---

# 6) Why Taskmaster MCP could help here

Yes — good fit. This is a bounded roadmap with checkable outputs (files, routes, commits). Give Taskmaster the single task from section 3; it’ll keep the run tight, avoid context bloat, and produce artifacts. Keep Serena enabled for the semantic jumps.

---

# 7) What you can do right now

* Replace your `CLAUDE.md` with the trimmed brief above.
* Kick off the “one-hour unattended task” (section 3).
* After it finishes, run through `/styleguide/stitch` and the five pages:

  * `/compose/stitch`
  * `/emails-unified/stitch`
  * `/accounts/stitch`
  * `/watchers/stitch`
  * `/rules/stitch`

if you want, I can also draft the actual `templates/styleguide/stitch.html` skeleton you can paste in as a starting point.
> **Job:** “Stitch polish + macro adoption + broken pages fix”
>
> **Goal:** Make UI consistent with `templates/styleguide/stitch.html`, adopt macros on Stitch pages, and fix high-priority broken screens.
>
> **Scope (must do):**
>
> 1. Import and use macros from `templates/stitch/_macros.html` in:
>
>    * `templates/stitch/emails-unified.html`
>    * `templates/stitch/rules.html`
>    * `templates/stitch/accounts.html`
>    * `templates/stitch/watchers.html`
> 2. Ensure main actions use `icon_btn` and statuses use `badge`.
> 3. Compose page: left-aligned layout, working “Back to Emails” link (done; re-check).
> 4. Accounts page: visible “Add Account” button at top; card actions link to real endpoints.
> 5. Email view (`/email/<id>`): apply Stitch layout container, toolbar with actions, and badge chips for status.
> 6. **Attachments 500:** implement graceful empty state, existence checks, and non-blocking response.
> 7. Sidebar active state for Stitch routes verified in `base.html` (done; re-check each).
>
> **Nice to have:**
>
> * Replace ad-hoc buttons with `icon_btn` everywhere in Stitch templates
> * Watchers spacing tightened to match styleguide tokens (done; re-check grid gaps)
>
> **Deliverables:**
>
> * New file: `templates/stitch/_macros.html`
> * Updated templates: emails, rules, accounts, watchers, email view
> * Small CSS additions in `static/css/stitch.components.css` if needed
> * Sanity test: visit
>
>   * `/styleguide/stitch`
>   * `/emails-unified/stitch`
>   * `/compose/stitch`
>   * `/rules/stitch`
>   * `/accounts/stitch`
>   * `/watchers/stitch`
>   * `/email/<id>` (with and without attachments)
>
> **Acceptance checks:**
>
> * No white button backgrounds anywhere
> * Hover overlays present on links
> * All action buttons use the same shape, spacing, and hover tints
> * Badges exactly match the styleguide
> * Accounts page shows “Add Account” button and working card actions
> * `/email/<id>` loads with Stitch layout and never throws 500 for attachments
>
> **Constraints:**
>
> * Dark theme, square corners, lime accent #bef264
> * Tailwind `tw-` prefix only, Bootstrap colors not used
> * Keep changes minimal and localized; don’t rename endpoints
>
> **Stop conditions:**
>
> * Any failing test in CI
> * Any template raises Jinja error
> * Any page shows white backgrounds on actions
>
> **Commit plan:**
>
> * `feat(stitch): add reusable macros (badge, icon_btn, table, toolbar)`
> * `fix(stitch): adopt macros in emails/rules/accounts/watchers; unify actions`
> * `fix(email): attachments API empty-state + safe path checks`
> * `chore(styleguide): finalize /styleguide/stitch and verify sidebar active states`

---
