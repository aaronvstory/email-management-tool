#!/usr/bin/env bash
set -euo pipefail

echo "🔐 Email Management Tool - Security Setup"
echo "=========================================="

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
else
  echo "✓ .env file exists"
fi

if ! grep -q "^FLASK_SECRET_KEY=" .env || grep -q "^FLASK_SECRET_KEY=$" .env; then
  echo "Generating FLASK_SECRET_KEY..."
  SECRET_KEY=$(python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)
  if grep -q "^FLASK_SECRET_KEY=" .env; then
    sed -i.bak "s/^FLASK_SECRET_KEY=.*/FLASK_SECRET_KEY=${SECRET_KEY}/" .env || true
  else
    echo "FLASK_SECRET_KEY=${SECRET_KEY}" >> .env
  fi
  echo "✓ SECRET_KEY generated"
else
  echo "✓ SECRET_KEY already configured"
fi

echo ""
echo "✅ Security setup complete!"
echo ""
echo "Next steps:"
echo "  1) Review .env and adjust values if needed"
echo "  2) Start app: python simple_app.py"
echo "  3) Run validation: ./validate_security.sh"
