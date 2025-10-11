# Ultimate Plan (Approved) — Execution Outline

This file captures the merged plan (best of Claude Opus + GPT‑5) we are executing now. Scope is surgical: fix edit persistence and release verification, prove interception prevents inbox delivery, add lightweight observability.

## Phases

1) Environment stabilization (Windows-safe)
- Stop stray python processes; remove SQLite WAL/SHM; create timestamped DB backup; ensure strong FLASK_SECRET_KEY via setup_security.ps1.

2) Edit that actually persists (CRITICAL)
- Server: Keep HELD guard; set `updated_at=CURRENT_TIMESTAMP`; commit; re‑SELECT row; return `{ ok, updated_fields, verified }`.
- Client: Fix template field mismatch (use `body_text`); POST to `/api/email/<id>/edit` with `{subject, body_text}`; rely on global CSRF fetch wrapper.
- Add thin GET alias `/email/<id>/edit` → reuses `/email/<id>/full`.

3) Release that truly delivers (CRITICAL)
- After IMAP APPEND, verify presence in target folder by Message‑ID; only then set `interception_status=RELEASED` and `status=DELIVERED`.

4) Prove interception prevents inbox delivery (gated)
- Live tests (ENABLE_LIVE_EMAIL_TESTS=1): send unique subject via SMTP proxy, assert not in INBOX while HELD, then release and assert edited subject appears in INBOX.

5) Worker heartbeats (observability)
- New table `worker_heartbeats(worker_id PRIMARY KEY, last_heartbeat, status)`; IMAP watcher upserts every 30s; `/healthz` reads recent entries (last 2m).

6) Minimal UI clarity
- Small alert in viewer when `interception_status=HELD`: “Not visible in recipient’s mailbox until release”.

## Acceptance criteria
1. Edit saves both subject and body_text; response includes verified values.
2. Intercepted emails absent from INBOX while HELD (IMAP SEARCH proof).
3. Released emails present in INBOX with edits applied.
4. `/healthz` shows worker heartbeats from DB.
5. CSRF enforced for JSON POSTs.

## Notes
- All DB changes are additive; rollback: revert commit + restore timestamped DB backup.
- Live tests are opt‑in to avoid network flakiness by default.
