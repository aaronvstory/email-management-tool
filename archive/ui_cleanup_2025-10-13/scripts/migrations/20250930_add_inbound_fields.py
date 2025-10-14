"""
Migration: Add inbound interception fields to email_messages table
Date: 2025-09-30
Purpose: Support rapid IMAP copy+purge inbound interception workflow
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'email_manager.db')

def up():
    """Add fields for inbound email interception"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get existing columns
    cur.execute("PRAGMA table_info(email_messages)")
    existing_cols = {row[1] for row in cur.fetchall()}
    
    # Add new columns if they don't exist
    migrations = [
        ("direction", "ALTER TABLE email_messages ADD COLUMN direction TEXT"),
        ("interception_status", "ALTER TABLE email_messages ADD COLUMN interception_status TEXT"),
        ("quarantine_folder", "ALTER TABLE email_messages ADD COLUMN quarantine_folder TEXT"),
        ("original_uid", "ALTER TABLE email_messages ADD COLUMN original_uid INTEGER"),
        ("original_internaldate", "ALTER TABLE email_messages ADD COLUMN original_internaldate TEXT"),        ("original_message_id", "ALTER TABLE email_messages ADD COLUMN original_message_id TEXT"),
        ("edited_message_id", "ALTER TABLE email_messages ADD COLUMN edited_message_id TEXT"),
        ("raw_path", "ALTER TABLE email_messages ADD COLUMN raw_path TEXT"),
        ("latency_ms", "ALTER TABLE email_messages ADD COLUMN latency_ms INTEGER"),
    ]
    
    for col_name, sql in migrations:
        if col_name not in existing_cols:
            print(f"Adding column: {col_name}")
            cur.execute(sql)
        else:
            print(f"Column already exists: {col_name}")
    
    # Create indexes for performance
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_messages_direction_status 
        ON email_messages(direction, interception_status)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_messages_original_uid 
        ON email_messages(original_uid)
    """)
    
    conn.commit()
    print("Migration completed successfully!")
    conn.close()

if __name__ == "__main__":
    up()