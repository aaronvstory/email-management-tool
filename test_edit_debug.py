"""Debug script to test email edit endpoint."""
import sqlite3
import requests
import json

DB_PATH = 'email_manager.db'

# Get a HELD email
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
row = cur.execute("""
    SELECT id, subject, body_text, interception_status, status
    FROM email_messages
    WHERE interception_status='HELD'
    LIMIT 1
""").fetchone()

if not row:
    print("No HELD emails found")
    conn.close()
    exit(1)

email_id = row['id']
print(f"Testing email ID: {email_id}")
print(f"Current subject: {row['subject']}")
print(f"Current body: {row['body_text'][:100]}...")
print(f"Status: {row['status']}, Interception: {row['interception_status']}")

# Test direct database update
print("\n=== Testing direct database update ===")
new_subject = "EDITED: " + (row['subject'] or 'No Subject')
new_body = "EDITED BODY: This has been edited for testing"

cur.execute("""
    UPDATE email_messages
    SET subject=?, body_text=?, updated_at=datetime('now')
    WHERE id=?
""", (new_subject, new_body, email_id))
print(f"Rows affected: {cur.rowcount}")
conn.commit()

# Verify update
updated = cur.execute("SELECT subject, body_text FROM email_messages WHERE id=?", (email_id,)).fetchone()
print(f"\nAfter direct update:")
print(f"Subject: {updated['subject']}")
print(f"Body: {updated['body_text']}")

# Rollback to original
cur.execute("""
    UPDATE email_messages
    SET subject=?, body_text=?
    WHERE id=?
""", (row['subject'], row['body_text'], email_id))
conn.commit()
conn.close()

print("\n=== Database test complete - update and rollback worked ===")
print("\nNow test the API endpoint...")
print("Note: API test requires authentication and CSRF token")
