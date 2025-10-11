#!/usr/bin/env python3
"""
Migration: Add email_notifications table for bounce/reject tracking
"""

import sqlite3

DB_PATH = "email_manager.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                notification_type TEXT,
                severity TEXT,
                message TEXT,
                user_id INTEGER,
                acknowledged BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES email_messages(id)
            )
        """)

        # Add index for quick lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_email_id
            ON email_notifications(email_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_acknowledged
            ON email_notifications(acknowledged)
        """)

        # Add bounce_reason column to email_messages if not exists
        cursor.execute("PRAGMA table_info(email_messages)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'bounce_reason' not in columns:
            cursor.execute("""
                ALTER TABLE email_messages
                ADD COLUMN bounce_reason TEXT
            """)
            print("✅ Added bounce_reason column")

        conn.commit()
        print("✅ Notifications table created successfully")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
