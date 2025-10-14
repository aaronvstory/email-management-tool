import os
import sys
import sqlite3


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import simple_app as sa

    app = sa.app
    app.config["TESTING"] = True

    conn = sqlite3.connect('email_manager.db')
    row = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not row:
        raise SystemExit('No admin user found')
    uid = row[0]

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(uid)
            sess['_fresh'] = True
        resp = client.get('/emails')
        assert resp.status_code == 200, f"GET /emails failed: {resp.status_code}"
        print('OK: /emails page loads')


if __name__ == '__main__':
    main()
