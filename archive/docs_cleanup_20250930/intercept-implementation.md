# (Moved) See archive/root_docs_20250930/intercept-implementation.md

# Intercept Implementation Plan (Inbound-Only, Mailbox Credentials)

This document orchestrates the implementation so Claude Code can build it step-by-step and interact with you as it goes. You will run Prompt 0 first, then proceed with Prompts 1–6. Each prompt includes success checks and asks Claude to pause and confirm before moving on.

Key intent:

- Prefer server-side hold via ManageSieve (Option A) whenever the mailbox provider supports it.
- Otherwise fall back to rapid IMAP hold-and-replace (Option B) using only mailbox credentials.
- No MX or tenant/provider routing changes.
- Integrate with this repo’s structure and Windows/UV tooling.

Repo context:

- Root: `c:/claude/Email-Management-Tool`
- Flask app: `app/` (services, routes, utils, web)
- DB: `email_manager.db` (SQLite)
- Existing IMAP/SMTP utilities may exist in `app/services` — we’ll add new components there.

---

## Prompt 0 — Overview, expectations, and interactive flow

You (Claude Code) are implementing inbound interception using only mailbox credentials. Work in small, verifiable steps. After each step:

- Run quick static checks (imports, lint if configured) and note results.
- Ask 1–2 clarifying questions if anything is ambiguous (hostnames, schema names, etc.).
- Wait for confirmation before proceeding to the next prompt.

What to build:

1. ManageSieve detector and manager (Option A): server-side “Quarantine” rule if supported.
2. Rapid IMAP hold-and-replace watcher (Option B): persistent IDLE, atomic MOVE to Quarantine, then APPEND edited mail to Inbox on approval.
3. Redelivery helpers: append edited MIME to Inbox, preserve chronology where possible.
4. Minimal DB additions for account mode and health status.
5. Light wiring to bootstrap per-account interception at startup (or via a script) without altering existing flows.

Definition of done:

- Accounts with ManageSieve: new inbound emails land directly in `Quarantine` (Inbox remains empty until approved/editorially replaced).
- Accounts without ManageSieve: watcher moves new mail from `INBOX` to `Quarantine` within ~200 ms median under normal conditions.
- Edited message can be appended back to `INBOX` and appears as the “real” message; original remains in `Quarantine`.

When unsure, ask. Pause after each prompt and confirm success before continuing.

---

## Prompt 1 — Dependencies and DB migration

Actions:

1. Add dependencies (dev machine):
   - `imapclient` (robust IMAP with IDLE/MOVE)
   - `backoff` (reconnect/backoff helpers)
   - `dnspython` (optional; SRV discovery for ManageSieve)
2. Add DB columns to `email_accounts` for interception state.

Files to add:

- `scripts/migrations/20250914_add_interception_fields.py` — adds tracking fields.

Content (reference implementation):

```python
import sqlite3

DB_PATH = 'email_manager.db'

def up():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(email_accounts)')
    cols = {row['name'] for row in cur.fetchall()}

    def maybe(sql):
        cur.execute(sql)

    if 'interception_mode' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN interception_mode TEXT DEFAULT 'unknown'")
    if 'sieve_status' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN sieve_status TEXT DEFAULT 'inactive'")
    if 'sieve_endpoint' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN sieve_endpoint TEXT")
    if 'last_probe_at' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_probe_at TEXT")
    if 'last_interception_ok_at' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_interception_ok_at TEXT")
    if 'last_error' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_error TEXT")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    up()
```

Run (Windows PowerShell):

```powershell
uv python scripts/migrations/20250914_add_interception_fields.py
```

Success checks:

- Migration runs without error.
- Columns appear via `PRAGMA table_info(email_accounts)`.
- Ask: Do we already have an `email_accounts` table with `imap_host`, `imap_username`, `imap_password`, and `email_address` columns? If not, request schema.

---

## Prompt 2 — ManageSieve minimal client + detector + manager (Option A)

Files to add:

- `app/services/sieve_client.py` — tiny ManageSieve client (STARTTLS, AUTH, CAPABILITY, PUTSCRIPT, SETACTIVE, GETSCRIPT).
- `app/services/sieve_detector.py` — SRV + heuristic endpoint discovery and TCP probe.
- `app/services/sieve_manager.py` — uses IMAP to ensure `Quarantine` exists; tries endpoints; installs and activates hold-all script.

Key script contents (reference snippets — implement nearly verbatim, adapt imports to this repo):

- ManageSieve client with methods: `connect()`, `capability()`, `starttls()`, `auth_plain()`, `listscripts()`, `putscript()`, `setactive()`, `getscript()`, `close()`.
- Detector producing candidate endpoints from domain and imap host; SRV `_sieve._tcp.domain` when available; fallback to `imap_host:4190`, `sieve.domain`, `managesieve.domain`, `mail.domain`.
- Manager method `try_activate_hold()` that:
  - Ensures `Quarantine` folder exists via IMAP.
  - Iterates candidate endpoints; connects with STARTTLS; AUTH with mailbox creds; checks SIEVE capabilities include `fileinto`; uploads and activates:
    ```sieve
    require ["fileinto"];
    fileinto "Quarantine";
    stop;
    ```
  - On success, returns `(endpoint, "active")` else `None`.

Success checks:

- Static imports OK.
- Unit-free tests: calling detector returns at least heuristic endpoints for placeholders.
- Ask: Confirm target IMAP host(s) and whether TLS/ports are standard for your accounts.

---

## Prompt 3 — IMAP rapid watcher (Option B)

Files to add:

- `app/services/imap_watcher.py` — thread that keeps a persistent IMAP connection, IDLEs, and instantly moves new mail to `Quarantine` (UID MOVE preferred, fallback COPY+DELETE+EXPUNGE). Marks quarantined copy `\Seen`.

Key behaviors:

- Create `Quarantine` folder if missing.
- Track `UIDNEXT` to compute the UID range to move after IDLE wakes.
- Gmail compatibility: `imapclient` will handle MOVE where supported; otherwise label semantics apply under the hood.

Success checks:

- Module imports and instantiates with sample creds.
- Ask: Provide one test mailbox to run against (dev/staging). If not available, we’ll mock later.

---

## Prompt 4 — Redelivery (APPEND) helper + approval hook

Files to add:

- `app/services/mail_redeliver.py` — function `append_edited_to_inbox(imap_host, username, password, mime_bytes, internaldate=None)` that IMAP APPENDs edited MIME into `INBOX` as unseen.
- (Optional) Add a conceptual Flask route in `app/routes/` (e.g., `routes/interception.py`) to call this after approval. This can be stubbed if routes are organized differently.

Success checks:

- Static import OK.
- Ask: Where do we store edited MIME? Point to existing table/column or specify a new one.

---

## Prompt 5 — Auto mode selection and bootstrap wiring

Files to add:

- `app/services/interception_bootstrap.py` — function `bootstrap_account(account_id, email_address, imap_host, username, password)` that:
  - Tries `SieveManager.try_activate_hold()`.
  - On success: updates DB fields (`interception_mode='sieve'`, `sieve_status='active'`, `sieve_endpoint=...`) and returns `'sieve'`.
  - On failure: sets `interception_mode='imap'`, starts `IMAPRapidInterceptor` thread, returns `'imap'`.
- `scripts/run_interceptors.py` — reads first active account (or all active accounts) from `email_accounts` and calls `bootstrap_account` for each; keeps process alive if any IMAP watchers are running.

Success checks:

- Dry run returns `'sieve'` or `'imap'` based on availability; no unhandled exceptions.
- Ask: Should we bootstrap all `is_active=1` accounts or a single selected account in dev?

---

## Prompt 6 — Tests and smoke flows

Add minimal tests/smoke checks (no secrets committed):

- `tests/test_sieve_detector.py` — unit tests for SRV/candidate generation (pure functions, no live sockets).
- `tests/test_imap_watcher_imports.py` — imports and constructs watcher class.
- Optional integration (run locally with env vars): `tests/integration/test_interception_flow.py` that:
  - Loads creds from env (e.g., `TEST_IMAP_HOST`, `TEST_IMAP_USER`, `TEST_IMAP_PASS`).
  - Starts watcher; sends a test email to the mailbox; asserts message lands in `Quarantine` within a timeout.
  - Skipped by default unless env vars are present.

Success checks:

- Unit tests pass locally.
- Integration test skipped without env, or passes when env provided.

---

## Operational notes

- Windows port and TLS: we only open client connections; no privileged ports required.
- Reliability: add exponential backoff on reconnect; measure latency from IDLE wake to MOVE completion for observability.
- Limits: push notifications and server-side forwards may still occur before move in Option B; Option A avoids this when supported.

---

## Quick “Try it” (developer)

```powershell
# 1) Migration
uv python scripts/migrations/20250914_add_interception_fields.py

# 2) Install deps
uv pip install imapclient backoff dnspython

# 3) Run bootstrap runner
uv python scripts/run_interceptors.py
```

If no active account is found or creds are missing, update the `email_accounts` table or create a seed row for a dev mailbox.

---

## Acceptance checklist (for you and Claude Code)

- [ ] Prompt 1 completed: migration added and ran; columns visible.
- [ ] Prompt 2 completed: sieve client/detector/manager files created; imports clean.
- [ ] Prompt 3 completed: imap watcher file created; class instantiates; no syntax errors.
- [ ] Prompt 4 completed: redelivery helper added; callable from route/service.
- [ ] Prompt 5 completed: bootstrap wiring added; runner script created; dry run returns a mode.
- [ ] Prompt 6 completed: unit tests added; integration test scaffolded.
- [ ] One real mailbox validated (either Sieve or IMAP rapid path).
- [ ] Dashboard shows pending Quarantine items (future enhancement; optional for this phase).

---

## Notes for implementers

- Always ask if any schema/paths differ in this repo; adapt accordingly.
- When in doubt about Gmail vs. standard IMAP behavior, default to standard IMAP first and add Gmail conditionals later.
- Keep secrets out of the repo. Use local `.env` or secure secret storage when running integration tests.

End of plan — proceed to Prompt 0 and work interactively.
