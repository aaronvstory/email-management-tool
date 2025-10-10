import os
import sys
import sqlite3


class _DummySMTP:
    def __init__(self, host, port, *args, **kwargs):
        self.host = host
        self.port = port
    def starttls(self):
        pass
    def login(self, u, p):
        pass
    def sendmail(self, f, t, m):
        return {}
    def quit(self):
        pass


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import simple_app as sa

    app = sa.app
    app.config['TESTING'] = True

    # Admin user
    conn = sqlite3.connect('email_manager.db')
    row = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
    if not row:
        conn.close()
        raise SystemExit('No admin user found')
    admin_id = row[0]

    # Get any active account id
    conn.row_factory = sqlite3.Row
    acc = conn.execute("SELECT id, email_address FROM email_accounts WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not acc:
        raise SystemExit('No active account to send from')

    # Stub smtplib
    import smtplib
    smtplib.SMTP = _DummySMTP  # type: ignore
    smtplib.SMTP_SSL = _DummySMTP  # type: ignore

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_id)
            sess['_fresh'] = True

        form = {
            'from_account': str(acc['id']),
            'to': acc['email_address'],
            'subject': 'Form Send',
            'body': 'Hello',
        }
        resp = client.post('/compose', data=form, follow_redirects=False)
        assert resp.status_code in (301, 302), f"Expected redirect, got {resp.status_code}"
        # Expect redirect to inbox
        loc = resp.headers.get('Location','')
        assert '/inbox' in loc, f"Unexpected redirect: {loc}"
        print('OK: Compose form POST redirects to /inbox')


if __name__ == '__main__':
    main()
