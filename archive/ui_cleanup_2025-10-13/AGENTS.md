# Repository Guidelines

## Project Structure & Module Organization
The Flask application lives in `app/`, split into `models/`, `routes/`, `services/`, `utils/`, and background `workers/`. UI assets reside in `templates/` and `static/`. Configuration defaults live in `config/config.ini` and environment overrides in `.env`; keep secrets out of version control. Local state such as `email_manager.db` and ad-hoc migration scripts under `migrations/` support quick developer setups. Operational utilities and e2e helpers are collected in `scripts/`, while reference material sits in `docs/` and historical notes in `archive/`. Tests mirror runtime packages inside `tests/` with focused suites like `tests/interception/` and `tests/email_flow/`.

## Build, Test, and Development Commands
Create or refresh the virtualenv with `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`. Run the full stack (SMTP proxy + dashboard) through `pwsh .\manage.ps1 start`; stop with `Ctrl+C` or `pwsh .\manage.ps1 stop`. For lightweight iteration use `python simple_app.py`, which enables Flask auto-reload. Validate setup changes and dependencies by invoking `python start.py`, and use scripts such as `python scripts/live_interception_e2e.py --dry-run` when reproducing interception issues.

## Coding Style & Naming Conventions
Format Python with `black` (88-character lines) and keep 4-space indentation. Modules, packages, and test files stay snake_case; Flask blueprints expose PascalCase classes but keep endpoint functions snake_case. Run `pylint app tests` and `mypy app` before submitting to catch regressions. Front-end templates follow Bootstrap 5; reuse existing class patterns in `static/css/` and avoid inline styling.

## Testing Guidelines
Use `pytest -q` for the default suite; target domains with commands like `pytest -q tests/interception` or `pytest tests/email_flow/test_edit_release_flow.py -vv`. Keep fixtures and reusable helpers in `tests/helpers/`, and mirror the runtime module names when creating new test packages. Document manual SMTP or dashboard checks in PR notes when touching email flow or UI logic.

## Commit & Pull Request Guidelines
Follow the Conventional Commits style observed in history (`feat(rate-limits): ...`, `style(ui): ...`). Squash noisy setup commits, and ensure formatting/lint passes before pushing. Pull requests should include: concise summary, test evidence (`pytest -q`, manual steps), linked GitHub issue, and screenshots or HAR captures when UI or API responses change. Request review from the platform maintainers channel before merging to `main`.

## Security & Configuration Tips
Never commit `.env`, `email_manager.db*`, or `archive/` snapshots; validate `.gitignore` updates whenever adding secrets or new asset dirs. Rotate SMTP credentials in `config/config.ini` plus `.env` and confirm `setup_security.ps1` passes before release builds. When enabling optional Sentry reporting, update DSNs in the environment only and verify the change via `python scripts/live_check.py --safety`.

## Agent Handoffs
Document interim state in `docs/` (e.g., `IMPLEMENTATION_SUMMARY.md`) and tag automation-ready tasks in `PLAN.md` before ending a shift. Leave reproducible instructions in `scripts/README` stubs or inline comments so monitoring agents can replay `scripts/live_*` flows without additional context.
