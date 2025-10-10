import os
import sys
import sqlite3


def _get_admin_user_id(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import simple_app as sa

    app = sa.app
    app.config["TESTING"] = True
    db_path = getattr(sa, "DB_PATH", None) or os.environ.get("DB_PATH", "email_manager.db")

    user_id = _get_admin_user_id(db_path)
    if not user_id:
        raise SystemExit("No admin user found in database; cannot simulate admin login.")

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

        # Inbox page should load
        r1 = client.get("/inbox")
        assert r1.status_code == 200, f"GET /inbox failed: {r1.status_code}"

        # Accounts page should load for admin
        r2 = client.get("/accounts")
        assert r2.status_code == 200, f"GET /accounts failed: {r2.status_code}"

        print("OK: Inbox and Accounts pages load (admin session).")


if __name__ == "__main__":
    main()
