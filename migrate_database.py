#!/usr/bin/env python3
"""
Database migration script to add account_id column to email_messages table
"""

import sqlite3
import os

DB_PATH = 'email_manager.db'

def migrate_database():
    """Add account_id column if it doesn't exist"""
    if not os.path.exists(DB_PATH):
        print("Database not found. Please run the application first to create it.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if account_id column exists
    cursor.execute("PRAGMA table_info(email_messages)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if 'account_id' not in column_names:
        print("Adding account_id column to email_messages table...")
        try:
            cursor.execute("""
                ALTER TABLE email_messages 
                ADD COLUMN account_id INTEGER REFERENCES email_accounts(id)
            """)
            conn.commit()
            print("✅ Successfully added account_id column")
        except sqlite3.OperationalError as e:
            print(f"❌ Error adding column: {e}")
    else:
        print("✅ account_id column already exists")
    
    # Check for review_notes column
    if 'review_notes' not in column_names:
        print("Adding review_notes column to email_messages table...")
        try:
            cursor.execute("""
                ALTER TABLE email_messages 
                ADD COLUMN review_notes TEXT
            """)
            conn.commit()
            print("✅ Successfully added review_notes column")
        except sqlite3.OperationalError as e:
            print(f"❌ Error adding review_notes column: {e}")
    else:
        print("✅ review_notes column already exists")
    
    # Check for other missing columns that might be needed
    missing_columns = []
    
    # Check email_accounts table for health status columns
    cursor.execute("PRAGMA table_info(email_accounts)")
    account_columns = cursor.fetchall()
    account_column_names = [col[1] for col in account_columns]
    
    health_columns = [
        ('smtp_health_status', 'TEXT'),
        ('imap_health_status', 'TEXT'),
        ('pop3_health_status', 'TEXT'),
        ('last_health_check', 'TIMESTAMP'),
        ('connection_status', 'TEXT'),
        ('last_successful_connection', 'TIMESTAMP'),
        ('pop3_host', 'TEXT'),
        ('pop3_port', 'INTEGER DEFAULT 995'),
        ('pop3_username', 'TEXT'),
        ('pop3_password', 'TEXT'),
        ('pop3_use_ssl', 'BOOLEAN DEFAULT 1'),
        ('provider_type', 'TEXT')
    ]
    
    for col_name, col_type in health_columns:
        if col_name not in account_column_names:
            print(f"Adding {col_name} column to email_accounts table...")
            try:
                cursor.execute(f"""
                    ALTER TABLE email_accounts 
                    ADD COLUMN {col_name} {col_type}
                """)
                conn.commit()
                print(f"✅ Successfully added {col_name} column")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Could not add {col_name}: {e}")
    
    conn.close()
    print("\n✅ Database migration complete!")

if __name__ == "__main__":
    migrate_database()