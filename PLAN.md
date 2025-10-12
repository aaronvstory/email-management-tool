# Finish-Line Plan — Email Management Tool

Status: Active
Owner(s): You (PM/Engineer), Droid (AI dev assistant)
Updated: <set by commits>

## Objective
Ship a reliable local email moderation tool that proves real-provider interception (hold → edit → release) across Gmail/Hostinger, with per‑account monitoring, robust watchers, and reproducible live tests.

## Guiding Principles
- Real provider behavior is the source of truth (live E2E must pass).
- Credentials live in DB (encrypted); UI controls start/stop per account.
- Minimal surprises: deterministic flows, actionable logs, safe defaults.

## Phase 0 — Pre‑flight (Do Now)
- [ ] Verify proxy & app health: GET /api/smtp-health and /healthz
- [ ] Confirm both accounts saved in DB with correct IMAP/SMTP + SSL
- [ ] Start Monitoring on each account (Accounts page)
- [ ] Test IMAP/SMTP via Accounts → Test

## Phase 1 — Live Baseline (Source of Truth)
- [ ] Set ENABLE_LIVE_EMAIL_TESTS=1 and run:
      python scripts/live_interception_e2e.py
- [ ] Record PASS/FAIL for Gmail→Hostinger and Hostinger→Gmail
- [ ] If FAIL, fix provider specifics (ports/SSL, usernames=email, app passwords), Quarantine folder naming; re‑run

## Phase 2 — IMAP Watcher Hardening
- [ ] Improve error taxonomy/logs: auth vs TLS vs MOVE unsupported vs timeouts
- [ ] Ensure unseen search and idempotent storage; reduce duplicate rows
- [ ] Surface worker heartbeats/circuit status in UI (Held/Diagnostics)
- [ ] Add quick restart button for a watcher (per account)

## Phase 3 — Edit/Release Fidelity
- [ ] Preserve headers; safely replace text/plain + HTML
- [ ] Attachment stripping notice appended reliably
- [ ] Handle HTML‑only and non‑UTF8 payloads; add regression tests
- [ ] Verify release by Message‑ID; robust fallback when missing

## Phase 4 — UX & Ops Polish
- [ ] Queue: clear status chips, disabled invalid actions, inline errors
- [ ] Navbar badge for SMTP/IMAP quick status
- [ ] Rotating logs + daily emergency backup cleanup (already scripted)

## Phase 5 — Tests & CI
- [ ] Add tests/conftest.py fixtures; stabilize non‑live subset
- [ ] CI job for stable tests (Windows)
- [ ] Manual "Live Test" workflow (requires secrets) — runs live_interception_e2e.py on demand

## Phase 6 — Rules & Provider Quality
- [ ] Extend rules: regex/sender/domain + thresholding
- [ ] Provider overrides table (folder names, quirks)

## Phase 7 — Documentation & Memory Bank
- [ ] Keep CLAUDE.md v2.8 in sync with features
- [ ] Update docs/TECHNICAL_DEEP_DIVE.md as features land
- [ ] Maintain .kilocode/rules/memory-bank/context.md after each milestone
## Definition of Done (Acceptance)
- Live E2E PASS both directions: not in INBOX while HELD; edited subject present after release
- Watchers start/stop per account; /healthz shows active heartbeats; diagnostics page green
- MIME edits correct (text+HTML), no secrets logged, logs actionable
- CI green on non‑live suite; manual Live Test workflow succeeds when run

## Risks & Mitigations
- Provider auth/app‑password issues → doc setup steps; fail‑fast diagnostics
- Folder mismatch → per‑account Quarantine override; verify at start
- DB contention → WAL + busy_timeout (done); keep writes short; retry on lock

## Runbook (Snippets)
```bash
# Start app
python simple_app.py

# Start/Stop watcher via API
POST /api/accounts/<id>/monitor/start
POST /api/accounts/<id>/monitor/stop

# Live E2E (requires ENABLE_LIVE_EMAIL_TESTS=1)
python scripts/live_interception_e2e.py

# Health
curl http://localhost:5000/api/smtp-health
curl http://localhost:5000/healthz
```

## Worklog
- <yyyy-mm-dd> Init PLAN.md and live E2E; per‑account watcher controls online — status: In Progress
- <yyyy-mm-dd> Hardening watchers and diagnostics UI — status: Planned

## Next Actions (Week 1)
- [ ] Phase 1: Run live_interception_e2e.py and capture results
- [ ] Phase 2: Add heartbeat status to Held/Diagnostics UI + richer logs
- [ ] Phase 3: Add MIME edge‑case handling with regression tests
- [ ] Update Memory Bank context.md with outcomes after each task
