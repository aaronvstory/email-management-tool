"""Verify that performance indices exist and are used by representative queries.

Outputs:
  - List of matching indices in sqlite_master
  - EXPLAIN QUERY PLAN for several dashboard/stat queries
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

def main(db_path: str = 'email_manager.db'):
    path = Path(db_path)
    if not path.exists():
        print(f"Database not found: {path}")
        return
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode")
    journal_mode = cur.fetchone()[0]
    print(f"Journal Mode: {journal_mode}")
    cur.execute("PRAGMA synchronous")
    print(f"Synchronous: {cur.fetchone()[0]}")
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_email_messages_%' ORDER BY 1")
    indices = [r[0] for r in cur.fetchall()]
    print("\nIndices Found:")
    for name in indices:
        print(f"  - {name}")
        # Get index columns using PRAGMA
        cur.execute(f"PRAGMA index_info({name})")
        cols = cur.fetchall()
        if cols:
            col_names = [c[2] for c in cols]
            print(f"    Columns: {', '.join(col_names)}")

    tests = [
        ("Global held count", "SELECT COUNT(*) FROM email_messages WHERE interception_status='HELD'"),
        ("Global pending count", "SELECT COUNT(*) FROM email_messages WHERE status='PENDING'"),
        ("Account held count", "SELECT COUNT(*) FROM email_messages WHERE account_id=1 AND interception_status='HELD'"),
        ("Account pending count", "SELECT COUNT(*) FROM email_messages WHERE account_id=1 AND status='PENDING'"),
        ("Account emails with ordering", "SELECT * FROM email_messages WHERE account_id=1 ORDER BY created_at DESC LIMIT 10"),
        ("Interception filter with sort", "SELECT * FROM email_messages WHERE interception_status='HELD' ORDER BY id DESC LIMIT 10"),
    ]
    print("\nQuery Plans:")
    for label, sql in tests:
        cur.execute(f"EXPLAIN QUERY PLAN {sql}")
        plan_rows = cur.fetchall()
        plan_desc = ' | '.join(r[-1] for r in plan_rows)
        print(f"- {label}: {plan_desc}")
    conn.close()

if __name__ == '__main__':
    main()
