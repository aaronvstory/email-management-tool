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

    # Get admin user id
    conn = sqlite3.connect('email_manager.db')
    row = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
    if not row:
        conn.close()
        raise SystemExit('No admin user found')
    admin_id = row[0]

    # Seed a pending email
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO email_messages (subject, sender, recipients, status)
        VALUES (?, ?, ?, 'PENDING')
        """,
        ("Test Subject", "sender@example.com", "[\"rcpt@example.com\"]"),
    )
    email_id = cur.lastrowid
    conn.commit()
    conn.close()

    try:
        with app.test_client() as client:
            # Login session
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin_id)
                sess['_fresh'] = True

            # Approve email
            resp = client.post(f"/email/{email_id}/action", data={"action": "APPROVE", "notes": "ok"}, follow_redirects=False)
            assert resp.status_code in (301, 302), f"Expected redirect, got {resp.status_code}"

        # Verify DB change
        conn2 = sqlite3.connect('email_manager.db')
        status = conn2.execute("SELECT status FROM email_messages WHERE id=?", (email_id,)).fetchone()[0]
        conn2.close()
        assert status == 'APPROVED', f"Email status not updated: {status}"

        print("OK: Approve action updates status and redirects")
    finally:
        # Cleanup inserted email
        conn3 = sqlite3.connect('email_manager.db')
        conn3.execute("DELETE FROM email_messages WHERE id=?", (email_id,))
        conn3.commit()
        conn3.close()


if __name__ == '__main__':
    main()
