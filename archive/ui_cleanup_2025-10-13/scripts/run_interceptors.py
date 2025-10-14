from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

from app.services.imap_watcher import AccountConfig, ImapWatcher


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("run_interceptors")


DB_PATH = Path(__file__).resolve().parents[1] / 'email_manager.db'


def load_active_accounts():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM email_accounts WHERE is_active = 1")
    except sqlite3.OperationalError as e:
        log.error("Failed to query email_accounts: %s", e)
        conn.close()
        return []
    rows = cur.fetchall()
    conn.close()
    accounts = []
    for r in rows:
        keys = r.keys()
        imap_port = r["imap_port"] if ("imap_port" in keys and r["imap_port"]) else 993
        accounts.append(
            AccountConfig(
                imap_host=r["imap_host"],
                imap_port=int(imap_port),
                username=r["imap_username"],
                password=r["imap_password"],
            )
        )
    return accounts


def main():
    accounts = load_active_accounts()
    if not accounts:
        log.warning("No active accounts found in %s", DB_PATH)
        return
    threads = []
    for cfg in accounts:
        watcher = ImapWatcher(cfg)
        t = threading.Thread(target=watcher.run_forever, name=f"imap-{cfg.username}", daemon=True)
        t.start()
        threads.append(t)
        log.info("Started watcher for %s", cfg.username)

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
