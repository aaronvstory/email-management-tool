#!/usr/bin/env bash
set -euo pipefail

# Email Management Tool — Linux launcher (Ubuntu 24.04 compatible)
# - Creates venv, installs deps, ensures system libs, and starts the app

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "==> Detecting Linux prerequisites"

# Ensure libmagic for python-magic on Debian/Ubuntu images
need_magic=0
python3 - <<'PY' || need_magic=1
try:
    import magic  # type: ignore
    print("python-magic OK")
except Exception:
    raise SystemExit(1)
PY

if [[ "$need_magic" -eq 1 ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "==> Installing libmagic1 via apt-get (requires network)"
    sudo_cmd=""
    if command -v sudo >/dev/null 2>&1; then sudo_cmd="sudo"; fi
    $sudo_cmd apt-get update -y
    $sudo_cmd apt-get install -y --no-install-recommends libmagic1
  else
    echo "WARNING: apt-get not available; python-magic may fail without libmagic. Install libmagic manually."
  fi
fi

echo "==> Creating Python virtual environment (.venv)"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -U pip setuptools wheel

echo "==> Installing project dependencies"
python -m pip install -r requirements.txt

# Optional: also install initial/requirements if needed by your workflows
if [[ -f initial/requirements.txt ]]; then
  python -m pip install -r initial/requirements.txt || true
fi

echo "==> Preparing environment"
# Listen on all interfaces in containers; disable watchers for first run
export FLASK_HOST="${FLASK_HOST:-0.0.0.0}"
export FLASK_PORT="${FLASK_PORT:-5000}"
export SMTP_PROXY_HOST="${SMTP_PROXY_HOST:-0.0.0.0}"
export SMTP_PROXY_PORT="${SMTP_PROXY_PORT:-8587}"
export ENABLE_WATCHERS="${ENABLE_WATCHERS:-0}"

# Kill anything bound to the same ports (best effort)
for p in "$FLASK_PORT" "$SMTP_PROXY_PORT"; do
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t -i :"$p" || true)
    if [[ -n "${pids:-}" ]]; then
      echo "==> Releasing port $p (killing: $pids)"
      kill -9 $pids || true
    fi
  fi
done

echo "==> Starting Email Management Tool"
exec python -u simple_app.py
