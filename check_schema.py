import sqlite3
conn = sqlite3.connect('email_manager.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(email_accounts)')
print("Columns in email_accounts table:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")
conn.close()