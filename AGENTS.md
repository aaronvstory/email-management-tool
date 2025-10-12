# Repository Guidelines

Use this quick reference alongside in-repo docs to keep updates consistent and production-ready.

## Project Structure & Module Organization
- Core Flask code lives in `app/`; feature logic sits under `models/`, `routes/`, `services/`, `utils/`, and background `workers/`.
- UI assets are in `templates/` and `static/`; match Bootstrap patterns already defined in `static/css/`.
- Config defaults stay in `config/config.ini`, while local overrides belong in `.env` (never commit secrets).
- Tests mirror runtime modules inside `tests/`, with focused suites such as `tests/interception/` and `tests/email_flow/`.
- Operational tooling sits in `scripts/`; working notes in `docs/`; historical artifacts in `archive/` (treat as read-only).

## Build, Test, and Development Commands
- `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt` — bootstrap or refresh dependencies.
- `pwsh .\manage.ps1 start` / `pwsh .\manage.ps1 stop` — run or halt the SMTP proxy plus dashboard stack.
- `python simple_app.py` — launch the Flask app with auto-reload for feature iteration.
- `python start.py` — validate environment wiring after setup changes.

## Coding Style & Naming Conventions
- Format Python with `black` (88-character line cap) and standard 4-space indentation.
- Lint with `pylint app tests` and type-check with `mypy app`; fix warnings before committing.
- Keep modules, packages, and tests in `snake_case`; expose Flask blueprints via PascalCase classes but keep endpoint functions snake_case.

## Testing Guidelines
- Use `pytest -q` for the default suite; narrow focus via `pytest -q tests/interception` or `pytest tests/email_flow/test_edit_release_flow.py -vv`.
- Place shared fixtures and helpers in `tests/helpers/` and mirror runtime structure for new suites.
- Note any manual SMTP proxy or dashboard verifications in PR descriptions, especially when email flows or UI change.

## Commit & Pull Request Guidelines
- Follow Conventional Commits, e.g., `feat(rate-limits): adjust burst threshold`.
- PRs should describe behavior changes, list test evidence (`pytest -q`, lint, mypy), link the tracking issue, and supply screenshots or HAR exports for UI/API diffs.
- Request review from the platform maintainers channel before merging to `main`.

## Security & Configuration Tips
- Do not commit `.env`, `email_manager.db*`, or `archive/` snapshots; update `.gitignore` when adding new secret-bearing paths.
- Rotate SMTP credentials consistently in `config/config.ini` and `.env`, then run `python scripts/live_check.py --safety` to confirm secure wiring.

## Agent Handoffs
- Summarize interim work in `docs/IMPLEMENTATION_SUMMARY.md` and queue follow-ups in `PLAN.md` before ending a shift.
- Leave replay-ready notes in `scripts/README` or inline comments so automation agents can execute `scripts/live_*` flows without extra context.
