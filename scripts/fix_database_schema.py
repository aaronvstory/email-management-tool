#!/usr/bin/env python3
"""
Database schema migration - Add missing columns to moderation_rules table
"""
import sqlite3
import sys

def migrate_database(db_path='email_manager.db'):
    """Add missing columns to moderation_rules table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    migrations = [
        ("rule_type", "TEXT DEFAULT 'keyword'"),
        ("condition_field", "TEXT DEFAULT 'subject'"),
        ("condition_operator", "TEXT DEFAULT 'contains'"),
        ("condition_value", "TEXT"),
    ]

    print(f"Migrating database: {db_path}")

    for column_name, column_def in migrations:
        try:
            cursor.execute(f"ALTER TABLE moderation_rules ADD COLUMN {column_name} {column_def}")
            print(f"✅ Added {column_name} column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"⏭️  {column_name} already exists")
            else:
                print(f"❌ Error adding {column_name}: {e}")
                return False

    conn.commit()
    conn.close()
    print("\n✅ Database migration complete!")
    return True

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'email_manager.db'
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
