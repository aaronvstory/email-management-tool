import os
import sys
import sqlite3
import smtplib


class _DummySMTP:
    def __init__(self, host, port, *args, **kwargs):
        self.host = host
        self.port = port
        self.logged_in = False
        self.started_tls = False

    # SMTP interface
    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.logged_in = True

    def sendmail(self, from_addr, to_addrs, msg):
        # No-op: simulate successful send
        return {}

    def quit(self):
        return True


def _get_any_user_id(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _get_any_active_account(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT id, email_address FROM email_accounts
            WHERE is_active = 1
            ORDER BY id LIMIT 1
            """
        ).fetchone()
        return (row[0], row["email_address"]) if row else (None, None)
    finally:
        conn.close()


def main():
    # Ensure project root on sys.path, then import the configured Flask app
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import simple_app as sa

    app = sa.app
    app.config["TESTING"] = True

    # Resolve DB path (default from app config or utils)
    db_path = getattr(sa, "DB_PATH", None) or os.environ.get("DB_PATH", "email_manager.db")

    user_id = _get_any_user_id(db_path)
    if not user_id:
        raise SystemExit("No users found in database; cannot simulate login.")

    from_account_id, from_address = _get_any_active_account(db_path)
    if not from_account_id:
        raise SystemExit("No active email account found in database; cannot compose.")

    # Monkeypatch smtplib to avoid real network calls
    smtplib.SMTP = _DummySMTP  # type: ignore
    smtplib.SMTP_SSL = _DummySMTP  # type: ignore

    with app.test_client() as client:
        # Simulate login by setting Flask-Login session
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

        # 1) GET /compose should load
        resp = client.get("/compose")
        assert resp.status_code == 200, f"GET /compose failed: {resp.status_code}"

        # 2) POST JSON to /compose should succeed (ok: True)
        payload = {
            "from_account": from_account_id,
            "to": from_address or "test@example.com",
            "subject": "Compose Route Test",
            "body": "Hello from automated test.",
        }
        resp2 = client.post("/compose", json=payload)
        assert resp2.status_code == 200, f"POST /compose failed: {resp2.status_code}"
        data = resp2.get_json()
        assert data and data.get("ok") is True, f"Unexpected response: {data}"

        print("OK: Compose GET and POST JSON passed (SMTP stubbed).")


if __name__ == "__main__":
    main()
