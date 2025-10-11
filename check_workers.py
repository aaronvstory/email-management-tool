#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('email_manager.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("IMAP Worker Heartbeats:")
rows = cur.execute('SELECT worker_id, last_heartbeat, status FROM worker_heartbeats ORDER BY last_heartbeat DESC').fetchall()
for r in rows:
    print(f"  {r['worker_id']}: {r['last_heartbeat']} - {r['status']}")

conn.close()