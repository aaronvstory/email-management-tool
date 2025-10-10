#!/usr/bin/env python3
"""Check test results in database"""

import sqlite3

conn = sqlite3.connect('email_manager.db')
cursor = conn.cursor()

# Count emails by status
cursor.execute('''
    SELECT interception_status, COUNT(*)
    FROM email_messages
    WHERE account_id IS NOT NULL
    GROUP BY interception_status
''')
status_counts = cursor.fetchall()

print("\n📊 Emails by Status (with account_id):")
for status, count in status_counts:
    print(f"   {status or 'NULL'}: {count}")

# Get recent emails with account_id
cursor.execute('''
    SELECT id, account_id, sender, subject, interception_status
    FROM email_messages
    WHERE account_id IS NOT NULL
    ORDER BY id DESC
    LIMIT 10
''')
recent = cursor.fetchall()

print("\n📧 Recent Emails with Account ID:")
for r in recent:
    sender = r[2][:30] if r[2] else "N/A"
    subject = r[3][:40] if r[3] else "N/A"
    print(f"   ID: {r[0]}, Account: {r[1]}, Status: {r[4]}")
    print(f"      From: {sender}")
    print(f"      Subject: {subject}")

# Count total emails with account_id
cursor.execute('SELECT COUNT(*) FROM email_messages WHERE account_id IS NOT NULL')
total = cursor.fetchone()[0]
print(f"\n✅ Total emails with account_id: {total}")

conn.close()