import os
import sys
os.environ["IMAP_LOG_VERBOSE"] = "1"

import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from app.services.imap_watcher import ImapWatcher, AccountConfig
from app.utils.crypto import decrypt_credential
import sqlite3

# Get Hostinger account config
conn = sqlite3.connect("email_manager.db")
cursor = conn.cursor()
row = cursor.execute("SELECT id, email_address, imap_host, imap_port, imap_username, imap_password FROM email_accounts WHERE id=2").fetchone()
conn.close()

if not row:
    print("ERROR: No Hostinger account found")
    sys.exit(1)

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

print(f"\n🔧 Manual IMAP fetch for account {account_id} ({email})")
print(f"📡 Connecting to {imap_host}:{imap_port}...")

watcher = ImapWatcher(cfg)
client = watcher._connect()

if not client:
    print("❌ Connection failed")
    sys.exit(1)

print(f"✅ Connected successfully")

# Manually trigger processing of new messages
print(f"\n🔍 Checking for new messages...")
watcher._client = client
watcher._handle_new_messages(client, {})

print(f"\n✅ Manual fetch complete")
watcher.close()
