#!/usr/bin/env python3
"""
Monitor for email interception in real-time
Checks database every 10 seconds for up to 5 minutes
"""

import sqlite3
import time
from datetime import datetime, timedelta

DB_PATH = "email_manager.db"
MAX_WAIT_MINUTES = 5
CHECK_INTERVAL_SECONDS = 10

def check_recent_interceptions():
    """Check for emails intercepted in the last 10 minutes"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Look for recent INVOICE emails
        cutoff_time = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

        results = cursor.execute("""
            SELECT id, sender, recipients, subject, created_at,
                   interception_status, status
            FROM email_messages
            WHERE subject LIKE '%INVOICE%Test%'
              AND created_at > ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (cutoff_time,)).fetchall()

        conn.close()

        return [dict(row) for row in results]

    except Exception as e:
        print(f"❌ Database error: {e}")
        return []

def monitor():
    """Monitor for interceptions with periodic updates"""
    print("=" * 70)
    print("CONTINUOUS INTERCEPTION MONITORING".center(70))
    print("=" * 70)
    print(f"\nMonitoring for up to {MAX_WAIT_MINUTES} minutes...")
    print(f"Checking database every {CHECK_INTERVAL_SECONDS} seconds\n")

    start_time = datetime.now()
    max_duration = timedelta(minutes=MAX_WAIT_MINUTES)

    found_emails = set()  # Track email IDs we've already reported

    iteration = 0
    while datetime.now() - start_time < max_duration:
        iteration += 1
        elapsed = (datetime.now() - start_time).total_seconds()

        emails = check_recent_interceptions()

        new_emails = [email for email in emails if email['id'] not in found_emails]

        if new_emails:
            for email in new_emails:
                print("\n" + "=" * 70)
                print(f"🎉 NEW INTERCEPTION DETECTED!")
                print("=" * 70)
                print(f"ID: {email['id']}")
                print(f"Subject: {email['subject']}")
                print(f"From: {email['sender']}")
                print(f"To: {email['recipients']}")
                print(f"Created: {email['created_at']}")
                print(f"Status: {email['status']}")
                print(f"Interception: {email['interception_status']}")
                print("=" * 70)

                found_emails.add(email['id'])

        if iteration % 3 == 0:  # Print status every 30 seconds
            print(f"[{int(elapsed)}s] Still monitoring... (found {len(found_emails)} emails so far)")

        time.sleep(CHECK_INTERVAL_SECONDS)

    print("\n" + "=" * 70)
    print("MONITORING COMPLETE".center(70))
    print("=" * 70)
    print(f"\nTotal emails intercepted: {len(found_emails)}")

    if len(found_emails) >= 2:
        print("\n✅ SUCCESS: Both test emails were intercepted!")
    elif len(found_emails) == 1:
        print("\n⚠️ PARTIAL: Only one test email was intercepted")
    else:
        print("\n❌ NO INTERCEPTIONS: Emails may not have arrived yet")
        print("   Check provider delivery times or IMAP watcher logs")

if __name__ == "__main__":
    monitor()
