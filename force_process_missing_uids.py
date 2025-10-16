"""
Force process UIDs 120-123 by manually resetting UIDNEXT tracker.

This script:
1. Connects to Hostinger IMAP
2. Manually resets _last_uidnext to 119 (last processed)
3. Forces processing of UIDs 120-123
4. Applies rules and moves to Quarantine if matched
"""
import os
os.environ["IMAP_LOG_VERBOSE"] = "1"

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from app.services.imap_watcher import ImapWatcher, AccountConfig
from app.utils.crypto import decrypt_credential
import sqlite3

# Get Hostinger account config
conn = sqlite3.connect("email_manager.db")
cursor = conn.cursor()
row = cursor.execute("SELECT id, email_address, imap_host, imap_port, imap_username, imap_password FROM email_accounts WHERE id=2").fetchone()

# Check last processed UID
last_uid_row = cursor.execute("SELECT MAX(original_uid) FROM email_messages WHERE account_id=2").fetchone()
last_processed_uid = last_uid_row[0] if last_uid_row and last_uid_row[0] else 0

conn.close()

if not row:
    print("❌ ERROR: No Hostinger account found")
    exit(1)

account_id, email, imap_host, imap_port, imap_username, imap_password = row
password = decrypt_credential(imap_password)

cfg = AccountConfig(
    imap_host=imap_host,
    imap_port=imap_port,
    username=imap_username or email,
    password=password,
    use_ssl=True,
    account_id=account_id,
    db_path="email_manager.db"
)

print(f"\n🔧 Force processing missing UIDs for account {account_id} ({email})")
print(f"📊 Last processed UID in database: {last_processed_uid}")
print(f"🎯 Target UIDs to process: 120, 121, 122, 123")
print(f"📡 Connecting to {imap_host}:{imap_port}...\n")

watcher = ImapWatcher(cfg)
client = watcher._connect()

if not client:
    print("❌ Connection failed")
    exit(1)

print(f"✅ Connected successfully")

# CRITICAL FIX: Override _last_uidnext to force processing of UIDs 120-123
print(f"\n🔄 Resetting _last_uidnext from {watcher._last_uidnext} to {last_processed_uid}")
watcher._last_uidnext = last_processed_uid  # Force it to check UIDs > 119

# Manually trigger processing
print(f"\n🔍 Manually triggering _handle_new_messages()...")
watcher._client = client
watcher._handle_new_messages(client, {})

print(f"\n✅ Processing complete")
watcher.close()

# Verify results
conn = sqlite3.connect("email_manager.db")
cursor = conn.cursor()
rows = cursor.execute('''
    SELECT id, original_uid, subject, interception_status
    FROM email_messages
    WHERE account_id = 2 AND original_uid >= 120
    ORDER BY original_uid
''').fetchall()

print(f"\n📈 Results: {len(rows)}/4 emails processed")
for r in rows:
    print(f"  ✅ ID:{r[0]} | UID:{r[1]} | Subj:{r[2][:40]} | Status:{r[3]}")

conn.close()
