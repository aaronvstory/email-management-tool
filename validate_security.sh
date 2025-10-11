#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Security Validation Tests"
echo "============================"

BASE=${BASE:-http://localhost:5000}

if ! curl -s "$BASE" >/dev/null 2>&1; then
  echo "❌ App not running at $BASE. Start with: python simple_app.py"
  exit 1
fi

echo ""
echo "Test 1: CSRF Protection (missing token)"
echo "---------------------------------------"
RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=admin&password=admin123")
if [ "$RESP" = "400" ]; then
  echo "✅ CSRF protection working (got 400 without token)"
else
  echo "❌ Expected 400, got $RESP"
fi

echo ""
echo "Test 2: Rate Limiting"
echo "----------------------"
echo "Sending 6 rapid login attempts (without token expected 400 until 429)..."
LIMITED=0
for i in 1 2 3 4 5 6; do
  RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "username=admin&password=wrong")
  if [ "$RESP" = "429" ]; then
    echo "  Attempt $i: 429 (rate limited) ✅"
    LIMITED=1
    break
  else
    echo "  Attempt $i: $RESP"
  fi
done
if [ "$LIMITED" = "1" ]; then
  echo "✅ Rate limiting triggered"
else
  echo "⚠️ No 429 observed; verify limiter configuration"
fi

echo ""
echo "Test 3: Manual Browser Validation"
echo "---------------------------------"
cat <<'TXT'
1. Open the app in a browser and go to /login
2. Submit login with valid CSRF (normal form submit) → should succeed or show proper error
3. Open DevTools → Network tab → ensure POSTs include X-CSRFToken header for AJAX requests
4. Verify compose/add account forms submit successfully
TXT

echo ""
echo "📊 Validation complete"
