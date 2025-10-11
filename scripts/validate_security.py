#!/usr/bin/env python3
"""
Validate security hardening: CSRF enforcement and login rate limiting.
Runs against the Flask app using its test_client (no external server needed).

Usage (from project root or scripts/ directory):
  python -m scripts.validate_security
"""
import sys
from pathlib import Path

# Ensure project root is importable when run from scripts/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup  # type: ignore
import os
import math
import re
from collections import Counter

# Load .env (if present) into process env BEFORE importing app
def _load_dotenv_into_environ() -> None:
    env_file = ROOT / '.env'
    if not env_file.exists():
        return
    try:
        text = env_file.read_text(encoding='utf-8', errors='ignore')
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k and v:
                # Do not print secrets; set only in-memory for this process
                os.environ[k] = v
    except Exception:
        pass

_load_dotenv_into_environ()

from simple_app import app

WEAK_SECRETS = {
    'dev-secret-change-in-production',
    'change-this-to-a-random-secret-key',
    'your-secret-here',
    'secret',
    'password',
    'flask-secret-key',
}


def calculate_entropy(s: str) -> float:
    """Shannon entropy in bits/char."""
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c/length) * math.log2(c/length) for c in counts.values())


def get_csrf_token(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    if meta and meta.get("content"):
        return meta["content"]
    # Fallback: hidden input in form
    inp = soup.find("input", attrs={"name": "csrf_token"})
    return inp.get("value") if inp else None


def test_missing_csrf_blocks_login(client) -> tuple[bool, int, str]:
    """Attempt valid credentials WITHOUT CSRF: should NOT land on dashboard.
    Accept a 400 response or a redirect back to /login as a pass.
    Returns (ok, status_code, location).
    """
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    loc = resp.headers.get("Location", "")
    ok = (resp.status_code == 400) or (300 <= resp.status_code < 400 and "/login" in loc and "/dashboard" not in loc)
    return ok, resp.status_code, loc


def test_valid_csrf_allows_login(client) -> tuple[bool, int, str]:
    """Attempt valid credentials WITH CSRF: should redirect to dashboard."""
    r = client.get("/login")
    token = get_csrf_token(r.data.decode("utf-8"))
    assert token, "CSRF token not found on /login page"

    resp = client.post(
        "/login",
        data={"username": "admin", "password": "admin123", "csrf_token": token},
        follow_redirects=False,
    )
    loc = resp.headers.get("Location", "")
    ok = (300 <= resp.status_code < 400) and "/dashboard" in loc
    return ok, resp.status_code, loc


def test_rate_limit_on_login(client) -> tuple[bool, list[int], dict]:
    """Trigger rate limit using JSON requests to force 429 response.
    Returns (ok, status_codes, last_headers).
    """
    # Acquire token from HTML, then use header for JSON posts
    r = client.get("/login")
    token = get_csrf_token(r.data.decode("utf-8"))
    assert token, "CSRF token not found on /login page"

    status_codes: list[int] = []
    last_headers: dict = {}
    for _ in range(6):
        resp = client.post(
            "/login",
            json={"username": "admin", "password": "wrong"},
            headers={
                "Accept": "application/json",
                "X-CSRFToken": token,
            },
        )
        status_codes.append(resp.status_code)
        last_headers = dict(resp.headers)

    # Expect at least one 429 and look for typical limiter headers
    ok = 429 in status_codes or last_headers.get("Retry-After") or last_headers.get("X-RateLimit-Remaining") == "0"
    return bool(ok), status_codes, last_headers


def check_secret_key_strength() -> tuple[bool, int, bool, float]:
    """Verify SECRET_KEY strength without printing it.
    Returns (ok, length, is_blacklisted_or_default, entropy_bits_per_char).
    Policy: length>=32, entropy>=4.0 bits/char, not in weak blacklist.
    """
    secret = app.config.get("SECRET_KEY") or ""
    s = str(secret)
    length = len(s)
    entropy = calculate_entropy(s)
    is_blacklisted = s in WEAK_SECRETS
    is_hex = re.match(r'^[0-9a-fA-F]{64,}$', s) is not None  # secrets.token_hex(32)
    ok = bool(s) and (length >= 32) and (not is_blacklisted) and (is_hex or entropy >= 4.0)
    return ok, length, is_blacklisted, entropy


def main() -> int:
    with app.test_client() as client:
        # 1) SECRET_KEY strength
        ok_secret, sk_len, is_blacklisted, ent = check_secret_key_strength()
        print(f"Test 0 (SECRET_KEY strength: len>=32, entropy>=4.0, not blacklisted): {'PASS' if ok_secret else 'FAIL'}  [len={sk_len}, blacklisted={is_blacklisted}, entropy={ent:.2f} bits/char]")

        # 2) CSRF negative: missing token blocks login
        miss_ok, miss_code, miss_loc = test_missing_csrf_blocks_login(client)
        print(f"Test 1 (missing CSRF blocks login): {'PASS' if miss_ok else 'FAIL'}  [status={miss_code}, location='{miss_loc}']")

        # 3) CSRF positive: valid token allows login
        valid_ok, valid_code, valid_loc = test_valid_csrf_allows_login(client)
        print(f"Test 2 (valid CSRF allows login): {'PASS' if valid_ok else 'FAIL'}  [status={valid_code}, location='{valid_loc}']")

        # 4) Rate limit via JSON (expect 429/headers)
        rl_ok, codes, headers = test_rate_limit_on_login(client)
        hdr_subset = {k: headers.get(k) for k in ('Retry-After', 'X-RateLimit-Remaining')}
        print(f"Test 3 (rate limit triggers 429/headers): {'PASS' if rl_ok else 'FAIL'}  [codes={codes}, headers_subset={hdr_subset}]")

    all_ok = ok_secret and miss_ok and valid_ok and rl_ok
    print("\nSummary:")
    print(f"  SECRET_KEY: {'OK' if ok_secret else 'NOT OK'} (len={sk_len}, entropy={ent:.2f} bpc)")
    print(f"  CSRF missing-token block: {'OK' if miss_ok else 'NOT OK'}")
    print(f"  CSRF valid-token success: {'OK' if valid_ok else 'NOT OK'}")
    print(f"  Rate limit: {'OK' if rl_ok else 'NOT OK'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
