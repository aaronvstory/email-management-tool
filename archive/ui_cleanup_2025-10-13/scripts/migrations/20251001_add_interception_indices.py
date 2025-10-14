"""Add useful indices for email_messages table (Phase 0 DB Hardening)

Indices added (if absent):
  idx_email_messages_interception_status      -> interception_status
  idx_email_messages_status                   -> status
  idx_email_messages_account_status           -> (account_id, status)
  idx_email_messages_account_interception     -> (account_id, interception_status)

Rationale:
- Dashboard & stats endpoints execute many COUNT(*) queries filtered by status or interception_status (with/without account_id)
- Composite indices speed per-account filtered queries while keeping single-column indices for global counts

Safe & Idempotent: Each CREATE INDEX guarded by sqlite_master check.
Rollback drops only indices this migration created.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / 'email_manager.db'

INDEX_SPECS = [
    ("idx_email_messages_interception_status", "CREATE INDEX idx_email_messages_interception_status ON email_messages (interception_status)"),
    ("idx_email_messages_status", "CREATE INDEX idx_email_messages_status ON email_messages (status)"),
    ("idx_email_messages_account_status", "CREATE INDEX idx_email_messages_account_status ON email_messages (account_id, status)"),
    ("idx_email_messages_account_interception", "CREATE INDEX idx_email_messages_account_interception ON email_messages (account_id, interception_status)")
]


def _index_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,))
    return cur.fetchone() is not None


def up(db_path: Path | None = None) -> None:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    created = []
    for name, ddl in INDEX_SPECS:
        if not _index_exists(cur, name):
            cur.execute(ddl)
            created.append(name)
    conn.commit()
    conn.close()
    print(f"Migration complete on {path}. Created indices: {created if created else 'NONE (already present)'}")


def down(db_path: Path | None = None) -> None:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    dropped = []
    for name, _ in INDEX_SPECS:
        if _index_exists(cur, name):
            cur.execute(f"DROP INDEX {name}")
            dropped.append(name)
    conn.commit()
    conn.close()
    print(f"Rollback complete on {path}. Dropped indices: {dropped if dropped else 'NONE'}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Add indices for email_messages table")
    p.add_argument('--down', action='store_true', help='Rollback (drop indices)')
    p.add_argument('--db', type=str, help='Override database path')
    args = p.parse_args()
    target = Path(args.db) if args.db else None
    if args.down:
        down(target)
    else:
        up(target)
