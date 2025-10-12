import sqlite3

conn = sqlite3.connect('email_manager.db')
cursor = conn.cursor()

# Check email accounts
cursor.execute('SELECT COUNT(*) FROM email_accounts')
accounts_count = cursor.fetchone()[0]
print(f'Email accounts: {accounts_count}')

# Check held emails
cursor.execute('SELECT COUNT(*) FROM email_messages WHERE interception_status="HELD"')
held_count = cursor.fetchone()[0]
print(f'Held emails: {held_count}')

# Check total emails
cursor.execute('SELECT COUNT(*) FROM email_messages')
total_emails = cursor.fetchone()[0]
print(f'Total emails: {total_emails}')

# Check if tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f'Tables: {[t[0] for t in tables]}')

conn.close()