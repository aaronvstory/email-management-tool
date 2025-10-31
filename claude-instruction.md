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

### `templates/styleguide/stitch.html`

```jinja
{% extends "base.html" %}
{% block title %}Stitch Styleguide{% endblock %}

{% block content %}
<div id="stitch_styleguide">
  <main class="tw-flex-1 tw-px-6 tw-py-4">
    <header class="tw-flex tw-items-center tw-justify-between tw-mb-4">
      <div>
        <h1 class="tw-text-2xl tw-font-bold tw-text-white">Stitch Styleguide</h1>
        <p class="tw-text-sm tw-text-zinc-400 tw-mt-1">Tokens, components, and patterns used across the app.</p>
      </div>
      <a href="{{ url_for('emails.emails_unified_stitch') }}"
         class="tw-inline-flex tw-items-center tw-gap-2 tw-text-primary tw-text-sm tw-font-medium tw-px-2 tw-py-1 hover:tw-bg-primary/10">
        <span class="material-symbols-outlined tw-!text-base">arrow_back</span>
        Back to Emails
      </a>
    </header>

    <!-- Local mini-nav -->
    <nav class="tw-flex tw-flex-wrap tw-gap-3 tw-mb-4">
      {% set sections = [
        ('tokens','Tokens'),
        ('typography','Typography'),
        ('buttons','Buttons'),
        ('links','Links & Hovers'),
        ('tabs','Nav Tabs'),
        ('badges','Status Badges'),
        ('forms','Forms'),
        ('tables','Tables'),
        ('cards','Cards & Panels'),
        ('sidebar','Sidebar Active Demo'),
        ('patterns','App Patterns')
      ] %}
      {% for id,label in sections %}
      <a href="#{{id}}" class="tw-text-sm tw-font-semibold tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">{{label}}</a>
      {% endfor %}
    </nav>

    <!-- TOKENS -->
    <section id="tokens" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Tokens</h2>
      <div class="tw-grid tw-grid-cols-2 md:tw-grid-cols-3 lg:tw-grid-cols-5 tw-gap-3">
        <!-- Row: core surfaces -->
        <div class="tw-bg-[#18181b] tw-border tw-border-border tw-p-3">
          <div class="tw-text-[12px] tw-text-zinc-400 tw-mb-1">bg</div>
          <div class="tw-text-zinc-200">#18181b</div>
        </div>
        <div class="tw-bg-[#27272a] tw-border tw-border-border tw-p-3">
          <div class="tw-text-[12px] tw-text-zinc-400 tw-mb-1">surface</div>
          <div class="tw-text-zinc-200">#27272a</div>
        </div>
        <div class="tw-bg-[#18181b] tw-border tw-border-[rgba(255,255,255,0.12)] tw-p-3">
          <div class="tw-text-[12px] tw-text-zinc-400 tw-mb-1">border</div>
          <div class="tw-text-zinc-200">rgba(255,255,255,.12)</div>
        </div>
        <div class="tw-bg-[#18181b] tw-border tw-border-border tw-p-3">
          <div class="tw-text-[12px] tw-text-zinc-400 tw-mb-1">text</div>
          <div class="tw-text-zinc-200">#e5e7eb</div>
        </div>
        <div class="tw-bg-[#18181b] tw-border tw-border-border tw-p-3">
          <div class="tw-text-[12px] tw-text-zinc-400 tw-mb-1">muted</div>
          <div class="tw-text-zinc-400">#9ca3af</div>
        </div>
        <!-- Row: accent + semantics -->
        <div class="tw-bg-[#bef264] tw-p-3">
          <div class="tw-text-[12px] tw-text-zinc-800 tw-mb-1">primary</div>
          <div class="tw-text-zinc-900 tw-font-semibold">#bef264</div>
        </div>
        <div class="tw-bg-[#a3d154] tw-p-3">
          <div class="tw-text-[12px] tw-text-zinc-800 tw-mb-1">primary-hover</div>
          <div class="tw-text-zinc-900 tw-font-semibold">#a3d154</div>
        </div>
        <div class="tw-bg-emerald-500/15 tw-border tw-border-transparent tw-p-3">
          <div class="tw-text-[12px] tw-text-emerald-400 tw-mb-1">success</div>
          <div class="tw-text-emerald-400">#22c55e</div>
        </div>
        <div class="tw-bg-amber-500/15 tw-border tw-border-transparent tw-p-3">
          <div class="tw-text-[12px] tw-text-amber-400 tw-mb-1">warning</div>
          <div class="tw-text-amber-400">#f59e0b</div>
        </div>
        <div class="tw-bg-red-500/15 tw-border tw-border-transparent tw-p-3">
          <div class="tw-text-[12px] tw-text-red-400 tw-mb-1">danger</div>
          <div class="tw-text-red-400">#ef4444</div>
        </div>
      </div>
    </section>

    <!-- TYPOGRAPHY -->
    <section id="typography" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Typography</h2>
      <div class="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 tw-gap-4">
        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <h1 class="tw-text-2xl tw-font-bold tw-text-white tw-mb-1">Page Title (2xl)</h1>
          <p class="tw-text-sm tw-text-zinc-400">Secondary line / description</p>
        </div>
        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <h3 class="tw-text-base tw-font-semibold tw-text-zinc-200 tw-mb-1">Section Header (base/bold)</h3>
          <p class="tw-text-sm tw-text-zinc-400">Body copy (sm)</p>
        </div>
      </div>
    </section>

    <!-- BUTTONS -->
    <section id="buttons" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Buttons</h2>
      <div class="tw-flex tw-flex-wrap tw-gap-3 tw-bg-background tw-border tw-border-border tw-p-4">
        <button class="tw-inline-flex tw-items-center tw-gap-2 tw-font-bold tw-text-zinc-900 tw-bg-primary tw-border tw-border-[#bef264] tw-px-4 tw-py-2 hover:tw-bg-[#a3d154]">
          <span class="material-symbols-outlined tw-!text-base">add</span> Primary
        </button>
        <button class="icon-btn-text icon-btn--primary">
          <span class="material-symbols-outlined tw-!text-base">edit</span> Ghost / Primary
        </button>
        <button class="icon-btn-text">
          <span class="material-symbols-outlined tw-!text-base">more_horiz</span> Ghost / Neutral
        </button>
        <button class="icon-btn-text icon-btn--danger">
          <span class="material-symbols-outlined tw-!text-base">delete</span> Danger
        </button>
      </div>
      <p class="tw-text-xs tw-text-zinc-500 tw-mt-2">Primary uses lime background; ghost uses transparent bg with subtle border and hover tints.</p>
    </section>

    <!-- LINKS -->
    <section id="links" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Links & Hovers</h2>
      <div class="tw-bg-background tw-border tw-border-border tw-p-4 tw-flex tw-gap-3 tw-flex-wrap">
        <a class="tw-text-sm tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">Neutral link</a>
        <a class="tw-text-sm tw-text-primary tw-px-2 tw-py-1 hover:tw-bg-primary/10">Primary link</a>
        <a class="tw-text-sm tw-text-zinc-300 tw-inline-flex tw-items-center tw-gap-2 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">
          <span class="material-symbols-outlined tw-!text-base">open_in_new</span> With icon
        </a>
      </div>
    </section>

    <!-- NAV TABS -->
    <section id="tabs" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Nav Tabs (filter strip)</h2>
      <nav class="tw-flex tw-items-center tw-gap-3 tw-bg-background tw-border tw-border-border tw-p-3">
        <a class="tw-text-sm tw-font-semibold tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">All <span class="tw-text-zinc-500 tw-ml-1">412</span></a>
        <a class="tw-text-sm tw-font-semibold tw-text-primary tw-px-2 tw-py-1 tw-border-b-[2px] tw-border-primary">Held <span class="tw-text-zinc-500 tw-ml-1">337</span></a>
        <a class="tw-text-sm tw-font-semibold tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">Released <span class="tw-text-zinc-500 tw-ml-1">75</span></a>
        <a class="tw-text-sm tw-font-semibold tw-text-zinc-300 tw-px-2 tw-py-1 hover:tw-bg-zinc-800/60">Rejected <span class="tw-text-zinc-500 tw-ml-1">0</span></a>
      </nav>
      <p class="tw-text-xs tw-text-zinc-500 tw-mt-2">Active tab uses lime text + bottom border; others get subtle hover overlay.</p>
    </section>

    <!-- BADGES -->
    <section id="badges" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Status Badges</h2>
      <div class="tw-bg-background tw-border tw-border-border tw-p-4 tw-flex tw-gap-3 tw-flex-wrap">
        <span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-amber-500/15 tw-text-amber-400">HELD</span>
        <span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-zinc-700 tw-text-zinc-400">FETCHED</span>
        <span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-green-500/15 tw-text-green-400">RELEASED</span>
      </div>
    </section>

    <!-- FORMS -->
    <section id="forms" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Forms</h2>
      <div class="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 tw-gap-4">
        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <label class="tw-text-sm tw-text-zinc-300 tw-font-medium">Input</label>
          <input type="text" placeholder="recipient@example.com"
                 class="tw-mt-2 tw-w-full tw-bg-[#1f1f23] tw-text-zinc-200 tw-text-sm tw-border tw-border-border tw-px-3 tw-py-2 focus:tw-outline-none focus:tw-border-[#bef264]" />
          <div class="tw-flex tw-gap-3 tw-mt-3">
            <select class="tw-bg-[#1f1f23] tw-text-zinc-200 tw-text-sm tw-border tw-border-border tw-px-3 tw-py-2 focus:tw-outline-none focus:tw-border-[#bef264]">
              <option>Select account…</option><option>Gmail</option><option>Hostinger</option>
            </select>
            <button class="tw-inline-flex tw-items-center tw-gap-2 tw-font-bold tw-text-zinc-900 tw-bg-primary tw-border tw-border-[#bef264] tw-px-4 tw-py-2 hover:tw-bg-[#a3d154]">
              <span class="material-symbols-outlined tw-!text-base">send</span> Submit
            </button>
          </div>
        </div>
        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <label class="tw-text-sm tw-text-zinc-300 tw-font-medium">Textarea</label>
          <textarea rows="4" class="tw-mt-2 tw-w-full tw-bg-[#1f1f23] tw-text-zinc-200 tw-text-sm tw-border tw-border-border tw-px-3 tw-py-2 focus:tw-outline-none focus:tw-border-[#bef264]"
                    placeholder="Type your message…"></textarea>
          <div class="tw-flex tw-items-center tw-gap-2 tw-mt-3">
            <input id="chk1" type="checkbox" class="tw-accent-[#bef264]" />
            <label for="chk1" class="tw-text-sm tw-text-zinc-300">Enable auto-save</label>
          </div>
        </div>
      </div>
    </section>

    <!-- TABLES -->
    <section id="tables" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Table</h2>
      <div class="tw-bg-background tw-border tw-border-border">
        <div class="tw-overflow-x-auto">
          <table class="tw-w-full tw-text-sm tw-text-left">
            <thead class="tw-text-zinc-400 tw-border-b tw-border-border">
              <tr>
                <th class="tw-px-4 tw-py-2">Time</th>
                <th class="tw-px-4 tw-py-2">Correspondents</th>
                <th class="tw-px-4 tw-py-2">Subject</th>
                <th class="tw-px-4 tw-py-2">Status</th>
                <th class="tw-px-4 tw-py-2 tw-text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="tw-divide-y tw-divide-[rgba(255,255,255,.06)]">
              <tr class="hover:tw-bg-zinc-800/40">
                <td class="tw-px-4 tw-py-3 tw-text-zinc-400">Oct 24, 07:11 AM</td>
                <td class="tw-px-4 tw-py-3">
                  <div class="tw-text-zinc-200">from billing@service.com</div>
                  <div class="tw-text-zinc-500">to you@example.com</div>
                </td>
                <td class="tw-px-4 tw-py-3 tw-text-zinc-200">
                  Your recent invoice <span class="tw-text-zinc-500">…</span>
                </td>
                <td class="tw-px-4 tw-py-3">
                  <span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-amber-500/15 tw-text-amber-400">HELD</span>
                </td>
                <td class="tw-px-4 tw-py-3">
                  <div class="tw-flex tw-justify-end tw-gap-2">
                    <button class="icon-btn-text icon-btn--primary"><span class="material-symbols-outlined tw-!text-base">visibility</span> View</button>
                    <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">download</span> Attachments</button>
                    <button class="icon-btn-text icon-btn--danger"><span class="material-symbols-outlined tw-!text-base">delete</span> Discard</button>
                  </div>
                </td>
              </tr>
              <tr class="hover:tw-bg-zinc-800/40">
                <td class="tw-px-4 tw-py-3 tw-text-zinc-400">Oct 24, 07:09 AM</td>
                <td class="tw-px-4 tw-py-3">
                  <div class="tw-text-zinc-200">from noreply@updates.com</div>
                  <div class="tw-text-zinc-500">to you@example.com</div>
                </td>
                <td class="tw-px-4 tw-py-3 tw-text-zinc-200">Status update <span class="tw-text-zinc-500">…</span></td>
                <td class="tw-px-4 tw-py-3">
                  <span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-green-500/15 tw-text-green-400">RELEASED</span>
                </td>
                <td class="tw-px-4 tw-py-3">
                  <div class="tw-flex tw-justify-end tw-gap-2">
                    <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">history</span> Details</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p class="tw-text-xs tw-text-zinc-500 tw-mt-2">Tight rows, subtle dividers, square chips, consistent action buttons.</p>
    </section>

    <!-- CARDS -->
    <section id="cards" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Cards & Panels</h2>
      <div class="tw-grid tw-grid-cols-1 lg:tw-grid-cols-2 tw-gap-4">
        <div class="tw-bg-background tw-border tw-border-border tw-flex tw-flex-col">
          <div class="tw-p-4 tw-border-b tw-border-border tw-flex tw-justify-between tw-items-center">
            <div>
              <h3 class="tw-text-zinc-200 tw-font-semibold">Gmail – Ndayisjecka</h3>
              <p class="tw-text-xs tw-text-zinc-500">imap.gmail.com:993 • smtp.gmail.com:587</p>
            </div>
            <div class="tw-flex tw-gap-2">
              <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">play_arrow</span> Start</button>
              <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">stop</span> Stop</button>
              <button class="icon-btn-text icon-btn--primary"><span class="material-symbols-outlined tw-!text-base">bug_report</span> Diagnostics</button>
            </div>
          </div>
          <div class="tw-p-4 tw-flex tw-gap-3 tw-flex-wrap">
            <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">mail</span> Test</button>
            <button class="icon-btn-text icon-btn--primary"><span class="material-symbols-outlined tw-!text-base">edit</span> Edit</button>
            <button class="icon-btn-text icon-btn--danger"><span class="material-symbols-outlined tw-!text-base">delete</span> Delete</button>
          </div>
        </div>

        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <div class="tw-flex tw-items-center tw-justify-between tw-mb-2">
            <h3 class="tw-text-zinc-200 tw-font-semibold">Toolbar Panel</h3>
            <div class="tw-flex tw-gap-2">
              <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">refresh</span> Refresh</button>
              <button class="icon-btn-text icon-btn--primary"><span class="material-symbols-outlined tw-!text-base">add</span> Add Item</button>
            </div>
          </div>
          <p class="tw-text-sm tw-text-zinc-400">Use this pattern for list headers with a right-aligned toolbar.</p>
        </div>
      </div>
    </section>

    <!-- SIDEBAR ACTIVE DEMO -->
    <section id="sidebar" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">Sidebar Active Demo</h2>
      <div class="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 tw-gap-4">
        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <p class="tw-text-sm tw-text-zinc-400 tw-mb-2">Active state should apply on stitch routes:</p>
          <ul class="tw-text-sm tw-text-zinc-300 tw-list-disc tw-pl-5">
            <li><code>emails.emails_unified_stitch</code></li>
            <li><code>compose.compose_stitch</code></li>
            <li><code>watchers.watchers_page_stitch</code></li>
            <li><code>moderation.rules_stitch</code></li>
            <li><code>accounts.email_accounts_stitch</code></li>
          </ul>
        </div>
        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <p class="tw-text-sm tw-text-zinc-400">Implementation lives in <code>templates/base.html</code> (endpoint checks).</p>
        </div>
      </div>
    </section>

    <!-- PATTERNS -->
    <section id="patterns" class="tw-mb-6">
      <h2 class="tw-text-lg tw-font-bold tw-text-white tw-mb-3">App Patterns</h2>
      <div class="tw-grid tw-grid-cols-1 lg:tw-grid-cols-2 tw-gap-4">
        <!-- Emails row pattern -->
        <div class="tw-bg-background tw-border tw-border-border tw-p-4">
          <h3 class="tw-text-zinc-200 tw-font-semibold tw-mb-3">Emails Row</h3>
          <div class="tw-flex tw-items-start tw-justify-between tw-gap-4 hover:tw-bg-zinc-800/40 tw-p-3">
            <div class="tw-flex-1">
              <div class="tw-text-zinc-400 tw-text-xs tw-mb-1">Oct 24, 07:11 AM</div>
              <div class="tw-text-zinc-200">Automated quarantine flow test <span class="tw-text-zinc-500">…</span></div>
              <div class="tw-text-zinc-500 tw-text-xs">from billing@service.com • to you@example.com</div>
            </div>
            <div class="tw-flex tw-items-center tw-gap-3">
              <span class="tw-inline-flex tw-items-center tw-text-[11px] tw-font-semibold tw-px-2 tw-py-[2px] tw-bg-amber-500/15 tw-text-amber-400">HELD</span>
              <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">download</span> Attachments</button>
              <button class="icon-btn-text icon-btn--primary"><span class="material-symbols-outlined tw-!text-base">check_circle</span> Release</button>
              <button class="icon-btn-text icon-btn--danger"><span class="material-symbols-outlined tw-!text-base">delete</span> Discard</button>
            </div>
          </div>
        </div>

        <!-- Accounts card pattern -->
        <div class="tw-bg-background tw-border tw-border-border tw-flex tw-flex-col">
          <div class="tw-p-4 tw-border-b tw-border-border tw-flex tw-justify-between tw-items-center">
            <h3 class="tw-text-zinc-200 tw-font-semibold">Email Accounts</h3>
            <a href="{{ url_for('accounts.add_email_account') }}"
               class="tw-inline-flex tw-items-center tw-gap-2 tw-font-bold tw-text-zinc-900 tw-bg-primary tw-border tw-border-[#bef264] tw-px-4 tw-py-2 hover:tw-bg-[#a3d154]">
              <span class="material-symbols-outlined tw-!text-xl">add_circle</span> Add Account
            </a>
          </div>
          <div class="tw-p-4 tw-grid tw-grid-cols-1 md:tw-grid-cols-2 tw-gap-3">
            <div class="tw-border tw-border-border tw-p-3">
              <div class="tw-flex tw-items-center tw-justify-between">
                <div>
                  <div class="tw-text-zinc-200 tw-font-semibold">Gmail</div>
                  <div class="tw-text-xs tw-text-zinc-500">ndayisjecka@gmail.com</div>
                </div>
                <div class="tw-flex tw-gap-2">
                  <button class="icon-btn-text icon-btn--primary"><span class="material-symbols-outlined tw-!text-base">edit</span> Edit</button>
                  <button class="icon-btn-text icon-btn--danger"><span class="material-symbols-outlined tw-!text-base">delete</span> Delete</button>
                </div>
              </div>
              <div class="tw-text-xs tw-text-zinc-500 tw-mt-2">imap.gmail.com:993 • smtp.gmail.com:587</div>
            </div>
            <div class="tw-border tw-border-border tw-p-3">
              <div class="tw-flex tw-items-center tw-justify-between">
                <div>
                  <div class="tw-text-zinc-200 tw-font-semibold">Hostinger</div>
                  <div class="tw-text-xs tw-text-zinc-500">mcintyre@corrinbox.com</div>
                </div>
                <div class="tw-flex tw-gap-2">
                  <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">play_arrow</span> Start</button>
                  <button class="icon-btn-text"><span class="material-symbols-outlined tw-!text-base">bug_report</span> Diagnostics</button>
                </div>
              </div>
              <div class="tw-text-xs tw-text-zinc-500 tw-mt-2">imap.hostinger.com:993 • smtp.hostinger.com:465</div>
            </div>
          </div>
        </div>
      </div>
    </section>

  </main>
</div>
{% endblock %}
```

---

### optional: add a route if you need it

```python
# in app/routes/styleguide.py (if not present)
from flask import Blueprint, render_template
from flask_login import login_required

styleguide_bp = Blueprint('styleguide', __name__)

@styleguide_bp.route('/styleguide/stitch')
@login_required
def stitch_styleguide():
    return render_template('styleguide/stitch.html')
```


---


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
