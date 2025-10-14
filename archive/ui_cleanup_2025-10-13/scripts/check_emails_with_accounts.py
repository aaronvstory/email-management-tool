#!/usr/bin/env python3
"""Check if emails are being stored with account_id"""

import sqlite3

conn = sqlite3.connect('email_manager.db')
cursor = conn.cursor()

# Get recent emails with account_id
cursor.execute('''
    SELECT id, account_id, sender, subject, interception_status, created_at
    FROM email_messages
    WHERE account_id IS NOT NULL
    ORDER BY id DESC LIMIT 5
''')
rows = cursor.fetchall()

print('Recent emails with account_id:')
for row in rows:
    print(f'ID: {row[0]}, Account: {row[1]}, From: {row[2][:30] if row[2] else "N/A"}, Subject: {row[3][:30] if row[3] else "N/A"}, Status: {row[4]}')

# Get total count
cursor.execute('SELECT COUNT(*) FROM email_messages WHERE account_id IS NOT NULL')
total = cursor.fetchone()[0]
print(f'\nTotal emails with account_id: {total}')

# Check recent emails without account_id
cursor.execute('''
    SELECT COUNT(*) FROM email_messages
    WHERE account_id IS NULL
''')
without = cursor.fetchone()[0]
print(f'Emails without account_id: {without}')

conn.close()