#!/usr/bin/env python3
"""
Validate security hardening: CSRF enforcement and login rate limiting.
Runs against the Flask app using its test_client (no external server needed).
"""
from bs4 import BeautifulSoup  # type: ignore
from simple_app import app


def get_csrf_token(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    if meta and meta.get("content"):
        return meta["content"]
    # Fallback: hidden input in form
    inp = soup.find("input", attrs={"name": "csrf_token"})
    return inp.get("value") if inp else None


def test_missing_csrf_returns_400(client) -> bool:
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.status_code == 400


def test_rate_limit_on_login(client) -> bool:
    # Acquire a valid token first
    r = client.get("/login")
    token = get_csrf_token(r.data.decode("utf-8"))
    assert token, "CSRF token not found on /login page"

    status_codes = []
    for _ in range(6):
        resp = client.post(
            "/login",
            data={"username": "admin", "password": "wrong", "csrf_token": token},
            follow_redirects=False,
        )
        status_codes.append(resp.status_code)
    return 429 in status_codes


def main() -> int:
    with app.test_client() as client:
        ok_csrf = test_missing_csrf_returns_400(client)
        print(f"Test 1 (missing CSRF → 400): {'PASS' if ok_csrf else 'FAIL'}")

        ok_rl = test_rate_limit_on_login(client)
        print(f"Test 2 (rate limit → 429):   {'PASS' if ok_rl else 'FAIL'}")

    all_ok = ok_csrf and ok_rl
    print("\nSummary:")
    print(f"  CSRF 400: {'OK' if ok_csrf else 'NOT OK'}")
    print(f"  429 RL:   {'OK' if ok_rl else 'NOT OK'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
