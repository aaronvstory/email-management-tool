#!/usr/bin/env python3
"""
Database migration script to add enhanced account management fields
"""

import sqlite3
import os

DB_PATH = 'data/emails.db'

def migrate_database():
    """Add new columns to email_accounts table for enhanced monitoring"""
    
    if not os.path.exists(DB_PATH):
        print("Database not found. Please run the application first to create it.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get current table schema
    cursor.execute("PRAGMA table_info(email_accounts)")
    existing_columns = {col[1] for col in cursor.fetchall()}
    
    migrations = []
    
    # Add provider_type column
    if 'provider_type' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN provider_type TEXT DEFAULT 'custom'",
                          "Added provider_type column"))
    
    # Add POP3 support columns
    if 'pop3_host' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN pop3_host TEXT",
                          "Added pop3_host column"))
    
    if 'pop3_port' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN pop3_port INTEGER DEFAULT 995",
                          "Added pop3_port column"))
    
    if 'pop3_username' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN pop3_username TEXT",
                          "Added pop3_username column"))
    
    if 'pop3_password' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN pop3_password TEXT",
                          "Added pop3_password column"))
    
    if 'pop3_use_ssl' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN pop3_use_ssl BOOLEAN DEFAULT 1",
                          "Added pop3_use_ssl column"))
    
    # Add enhanced monitoring columns
    if 'connection_status' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN connection_status TEXT DEFAULT 'unknown'",
                          "Added connection_status column"))
    
    if 'last_successful_connection' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN last_successful_connection TIMESTAMP",
                          "Added last_successful_connection column"))
    
    if 'total_emails_processed' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN total_emails_processed INTEGER DEFAULT 0",
                          "Added total_emails_processed column"))
    
    if 'smtp_use_tls' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN smtp_use_tls BOOLEAN DEFAULT 0",
                          "Added smtp_use_tls column"))
    
    # Add health check columns
    if 'imap_health_status' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN imap_health_status TEXT DEFAULT 'unknown'",
                          "Added imap_health_status column"))
    
    if 'smtp_health_status' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN smtp_health_status TEXT DEFAULT 'unknown'",
                          "Added smtp_health_status column"))
    
    if 'pop3_health_status' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN pop3_health_status TEXT DEFAULT 'unknown'",
                          "Added pop3_health_status column"))
    
    if 'last_health_check' not in existing_columns:
        migrations.append(("ALTER TABLE email_accounts ADD COLUMN last_health_check TIMESTAMP",
                          "Added last_health_check column"))
    
    # Execute migrations
    if migrations:
        print(f"Executing {len(migrations)} migrations...")
        for sql, description in migrations:
            try:
                cursor.execute(sql)
                print(f"✓ {description}")
            except sqlite3.OperationalError as e:
                print(f"✗ Failed: {description} - {e}")
        
        conn.commit()
        print(f"\n✅ Database migration completed successfully!")
    else:
        print("✅ Database is already up to date!")
    
    conn.close()

if __name__ == '__main__':
    migrate_database()