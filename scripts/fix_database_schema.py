#!/usr/bin/env python3
"""
Database schema migration - Add missing columns to moderation_rules table
This migration adds the extended schema columns while keeping the old keyword-based columns.
"""
import sqlite3
import sys
import os

def migrate_database(db_path='email_manager.db'):
    """Add missing columns to moderation_rules table"""

    if not os.path.exists(db_path):
        print(f"⚠️  Database not found: {db_path}")
        print("Creating new database with full schema...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Database will be created by SQLAlchemy, just return
        conn.close()
        return True

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if moderation_rules table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='moderation_rules'")
    if not cursor.fetchone():
        print("⚠️  moderation_rules table does not exist - will be created by SQLAlchemy")
        conn.close()
        return True

    migrations = [
        ("rule_type", "TEXT DEFAULT 'keyword'"),
        ("condition_field", "TEXT"),
        ("condition_operator", "TEXT"),
        ("condition_value", "TEXT"),
        ("action", "TEXT DEFAULT 'hold'"),
        ("priority", "INTEGER DEFAULT 100"),
        ("created_at", "TEXT DEFAULT ''"),
    ]

    print(f"Migrating database: {db_path}")
    print(f"Adding extended schema columns to moderation_rules table...\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for column_name, column_def in migrations:
        try:
            cursor.execute(f"ALTER TABLE moderation_rules ADD COLUMN {column_name} {column_def}")
            print(f"✅ Added {column_name} column")
            success_count += 1
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"⏭️  {column_name} already exists")
                skip_count += 1
            else:
                print(f"❌ Error adding {column_name}: {e}")
                error_count += 1

    conn.commit()

    # Display current schema
    print("\n📋 Current moderation_rules schema:")
    cursor.execute("PRAGMA table_info(moderation_rules)")
    for row in cursor.fetchall():
        print(f"   {row[1]:20s} {row[2]:15s} {'NOT NULL' if row[3] else ''} {f'DEFAULT {row[4]}' if row[4] else ''}")

    conn.close()

    print(f"\n{'='*60}")
    print(f"Migration Summary:")
    print(f"  ✅ Added: {success_count}")
    print(f"  ⏭️  Skipped (already exist): {skip_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"{'='*60}")

    if error_count > 0:
        print("\n⚠️  Migration completed with errors")
        return False

    print("\n✅ Database migration complete!")
    return True

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'email_manager.db'
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
