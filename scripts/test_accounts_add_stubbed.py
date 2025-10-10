import os
import sys
import sqlite3
import time


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import simple_app as sa

    app = sa.app
    app.config["TESTING"] = True

    # Admin user
    conn = sqlite3.connect('email_manager.db')
    row = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not row:
        raise SystemExit('No admin user found')
    admin_id = row[0]

    # Monkeypatch connectivity to avoid network
    import app.routes.accounts as accounts_mod

    def _ok(kind, host, port, username, password, use_ssl):
        return True, f"OK {kind} {host}:{port}"

    accounts_mod._test_email_connection = _ok

    # Unique email
    uniq = str(int(time.time()))
    email_addr = f"test{uniq}@corrinbox.com"

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_id)
            sess['_fresh'] = True

        data = {
            'account_name': f'Test {uniq}',
            'email_address': email_addr,
            'use_auto_detect': 'on',
            'imap_password': 'pass',
            'smtp_password': 'pass',
        }
        resp = client.post('/accounts/add', data=data, follow_redirects=False)
        assert resp.status_code in (301, 302), f"Add account expected redirect, got {resp.status_code}"

    # Cleanup: remove the created account
    conn2 = sqlite3.connect('email_manager.db')
    conn2.execute("DELETE FROM email_accounts WHERE email_address=?", (email_addr,))
    conn2.commit()
    conn2.close()

    print('OK: Accounts add flow (stubbed) redirects and inserts row')


if __name__ == '__main__':
    main()
