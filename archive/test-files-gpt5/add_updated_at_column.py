#!/usr/bin/env python3
"""Add updated_at column to email_messages table if missing"""

import sqlite3

DB_PATH = "email_manager.db"

def add_updated_at_column():
    """Add updated_at column to email_messages table"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute('PRAGMA table_info(email_messages)')
    columns = [col[1] for col in cursor.fetchall()]

    if 'updated_at' not in columns:
        print("Adding updated_at column to email_messages table...")
        try:
            cursor.execute('''
                ALTER TABLE email_messages
                ADD COLUMN updated_at TIMESTAMP
            ''')
            conn.commit()
            print("✅ Successfully added updated_at column")
        except Exception as e:
            print(f"❌ Error adding column: {e}")
    else:
        print("✅ updated_at column already exists")

    # Show current columns
    cursor.execute('PRAGMA table_info(email_messages)')
    columns = cursor.fetchall()
    print("\nCurrent columns in email_messages table:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    add_updated_at_column()