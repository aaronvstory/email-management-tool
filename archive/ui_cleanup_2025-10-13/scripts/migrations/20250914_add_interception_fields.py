import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / 'email_manager.db'


def _table_exists(cur, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def up():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Ensure email_accounts exists with minimal fields if missing
    if not _table_exists(cur, 'email_accounts'):
        cur.execute(
            '''CREATE TABLE email_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT UNIQUE NOT NULL,
                email_address TEXT NOT NULL,
                imap_host TEXT NOT NULL,
                imap_port INTEGER DEFAULT 993,
                imap_username TEXT NOT NULL,
                imap_password TEXT NOT NULL,
                smtp_host TEXT,
                smtp_port INTEGER DEFAULT 465,
                smtp_username TEXT,
                smtp_password TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )'''
        )

    cur.execute('PRAGMA table_info(email_accounts)')
    cols = {row['name'] for row in cur.fetchall()}

    def maybe(sql: str):
        cur.execute(sql)

    if 'interception_mode' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN interception_mode TEXT DEFAULT 'unknown'")
    if 'sieve_status' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN sieve_status TEXT DEFAULT 'inactive'")
    if 'sieve_endpoint' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN sieve_endpoint TEXT")
    if 'last_probe_at' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_probe_at TEXT")
    if 'last_interception_ok_at' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_interception_ok_at TEXT")
    if 'last_error' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_error TEXT")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    up()
    print(f"Migration complete on {DB_PATH}")
