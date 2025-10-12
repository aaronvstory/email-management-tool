# Repository Guidelines

## Project Structure & Module Organization
- Core Flask code resides in `app/`; feature modules split across `models/`, `routes/`, `services/`, `utils/`, and background `workers/`.
- UI templates and assets live in `templates/` and `static/`, following the Bootstrap patterns defined in `static/css/`.
- Configuration defaults belong in `config/config.ini`; keep local secrets in `.env` (never commit).
- Tests mirror runtime packages inside `tests/`, with suites such as `tests/interception/` and `tests/email_flow/`; place shared fixtures under `tests/helpers/`.
- Operational scripts sit in `scripts/`, reference docs in `docs/`, and historical artifacts in `archive/` (read-only).

## Build, Test, and Development Commands
- `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt` — create or refresh the Windows virtual environment and dependencies.
- `pwsh .\manage.ps1 start` / `pwsh .\manage.ps1 stop` — spin up or shut down the SMTP proxy plus dashboard stack.
- `python simple_app.py` — run the Flask app with auto-reload for feature work.
- `python start.py` — verify environment wiring after configuration changes.
- `pytest -q` — execute the default automated test suite; add paths (e.g., `pytest -q tests/interception`) to narrow scope.

## Coding Style & Naming Conventions
- Format Python with `black` (88-character limit) and 4-space indentation.
- Lint via `pylint app tests` and type-check with `mypy app`; resolve warnings before committing.
- Use `snake_case` for modules, packages, functions, and tests; expose Flask blueprints via PascalCase classes while keeping endpoint functions snake_case.

## Testing Guidelines
- Write tests alongside runtime modules, keeping naming consistent with the target package.
- Prefer focused suites (`tests/email_flow/test_edit_release_flow.py -vv`) when troubleshooting.
- Record any manual verification of SMTP proxy or dashboard behaviors in PR descriptions.

## Commit & Pull Request Guidelines
- Follow Conventional Commits, e.g., `feat(rate-limits): adjust burst threshold`.
- PRs should describe behavior changes, list test evidence (pytest, lint, mypy), link the tracking issue, and attach UI/API artifacts when relevant.
- Request review from the platform maintainers channel before merging to `main`.

## Security & Configuration Tips
- Do not commit `.env`, `email_manager.db*`, or snapshots from `archive/`; update `.gitignore` for new secret paths.
- Rotate SMTP credentials in both `config/config.ini` and `.env`, then run `python scripts/live_check.py --safety` to confirm secure wiring.

## Agent Handoffs
- Summarize work-in-progress in `docs/IMPLEMENTATION_SUMMARY.md` and queue follow-ups in `PLAN.md` before ending a shift.
- Leave actionable notes in `scripts/README` or inline comments so automation agents can run `scripts/live_*` flows without extra context.
