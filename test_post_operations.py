#!/usr/bin/env python3
"""Utility script for validating authenticated POST flows against the Stitch UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import requests
from bs4 import BeautifulSoup


DEFAULT_BASE_URL = "http://localhost:5020"
PLACEHOLDER_PREFIXES = {"CHANGE_ME", "CHANGE_ME_USERNAME", "CHANGE_ME_PASSWORD"}
REQUEST_TIMEOUT_SECONDS = 10


def _load_env_file() -> None:
    """Populate ``os.environ`` with keys from a sibling .env file if present."""

    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        os.environ.setdefault(key, value)


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().upper()
    if not normalized:
        return True

    return any(normalized == prefix or normalized.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES)


def _get_base_url() -> str:
    _load_env_file()
    base_url = os.getenv("EMAIL_MANAGER_BASE_URL", DEFAULT_BASE_URL).strip()
    return (base_url or DEFAULT_BASE_URL).rstrip("/")


def _get_credentials() -> Tuple[str, str]:
    _load_env_file()
    username = os.getenv("EMAIL_MANAGER_USERNAME", "").strip()
    password = os.getenv("EMAIL_MANAGER_PASSWORD", "").strip()

    if _is_placeholder(username) or _is_placeholder(password):
        raise RuntimeError(
            "Set EMAIL_MANAGER_USERNAME and EMAIL_MANAGER_PASSWORD before running this script. "
            "Populate them via environment variables or the local .env file."
        )

    if not username or not password:
        raise RuntimeError(
            "Missing EMAIL_MANAGER_USERNAME or EMAIL_MANAGER_PASSWORD environment values."
        )

    return username, password


def _extract_csrf_token(html: str) -> str:
    """Extract a CSRF token from the login form HTML."""

    soup = BeautifulSoup(html, "html.parser")
    csrf_input = soup.find("input", {"name": "csrf_token"})
    if not csrf_input:
        raise RuntimeError("Unable to locate CSRF token on login page.")

    raw_value = csrf_input.get("value")
    if isinstance(raw_value, (list, tuple)):
        raw_value = raw_value[0] if raw_value else ""

    token = str(raw_value or "").strip()
    if not token:
        raise RuntimeError("CSRF token input missing value attribute.")

    return token


def test_login() -> Tuple[requests.Session, bool]:
    """Test 1: Attempt login with CSRF handling."""

    base_url = _get_base_url()
    username, password = _get_credentials()

    print("=" * 60)
    print("TEST 1: Login POST with CSRF")
    print("=" * 60)

    session = requests.Session()

    response = session.get(f"{base_url}/login", timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    csrf_token = _extract_csrf_token(response.text)
    print("\u2713 CSRF token extracted from login page")

    login_data = {
        "username": username,
        "password": password,
        "csrf_token": csrf_token,
    }

    response = session.post(
        f"{base_url}/login",
        data=login_data,
        allow_redirects=False,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    print(f"\u2713 POST /login returned: {response.status_code}")
    print(f"\u2713 Redirect location: {response.headers.get('Location', 'None')}")

    if response.status_code == 302:
        redirect_url = response.headers.get("Location")
        if redirect_url and "/dashboard" in redirect_url:
            print("\u2713 Login successful - redirected to dashboard")
            return session, True

        print("\u26A0 Login redirected but not to dashboard")
        return session, False

    print("\u26A0 Login did not produce an HTTP 302 redirect")
    return session, False


def test_api_post(session: requests.Session) -> bool:
    """Test 2: Call a protected API endpoint after authentication."""

    base_url = _get_base_url()

    print("\n" + "=" * 60)
    print("TEST 2: API POST Operation")
    print("=" * 60)

    response = session.get(
        f"{base_url}/api/interception/held",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    print(f"\u2713 GET /api/interception/held returned: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\u2713 Response data: held_count={data.get('held_count', 'N/A')}")
        return True

    print(f"\u26A0 API call failed: {response.status_code}")
    return False


def test_dashboard_access(session: requests.Session) -> bool:
    """Test 3: Access the dashboard page while authenticated."""

    base_url = _get_base_url()

    print("\n" + "=" * 60)
    print("TEST 3: Dashboard Access (authenticated)")
    print("=" * 60)

    response = session.get(
        f"{base_url}/dashboard",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    print(f"\u2713 GET /dashboard returned: {response.status_code}")

    if response.status_code == 200:
        print("\u2713 Dashboard accessible")
        return True

    if response.status_code == 302:
        print("\u26A0 Redirected (not authenticated?)")
        return False

    print(f"\u26A0 Unexpected status: {response.status_code}")
    return False


if __name__ == "__main__":
    try:
        session, login_success = test_login()

        if login_success:
            test_api_post(session)
            test_dashboard_access(session)

            print("\n" + "=" * 60)
            print("\u2713 ALL TESTS COMPLETED SUCCESSFULLY")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("\u26A0 Login test failed - skipping other tests")
            print("=" * 60)

    except Exception as exc:  # noqa: BLE001 - user-facing script
        print(f"\n\u2717 Error: {exc}")
        import traceback

        traceback.print_exc()
