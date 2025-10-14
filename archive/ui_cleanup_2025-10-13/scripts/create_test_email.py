#!/usr/bin/env python3
"""
Create a test pending email for manual testing of the edit functionality
"""

import sqlite3
from datetime import datetime

DB_PATH = "email_manager.db"

def create_test_email():
    """Create a test pending email"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create test emails with various content
    test_emails = [
        {
            'message_id': f'manual_test_1_{datetime.now().timestamp()}@test.com',
            'sender': 'john.doe@example.com',
            'recipients': 'manager@company.com',
            'subject': 'Q4 Budget Report - Needs Review',
            'body_text': '''Dear Manager,

Please find attached the Q4 budget report for your review.

Key highlights:
- Revenue increased by 15%
- Operating costs reduced by 8%
- Net profit margin improved to 22%

This email requires editing before sending to ensure all figures are accurate.

Best regards,
John Doe
Finance Department''',
            'body_html': '<p>HTML version of the email</p>',
            'status': 'PENDING',
            'risk_score': 65,
            'keywords_matched': 'budget,report,financial'
        },
        {
            'message_id': f'manual_test_2_{datetime.now().timestamp()}@test.com',
            'sender': 'support@service.com',
            'recipients': 'customer@email.com',
            'subject': 'Your Support Ticket #12345 - Update Required',
            'body_text': '''Hello,

We need to update you on your support ticket.

Current Status: In Progress
Priority: High
Expected Resolution: Within 24 hours

Please edit this template with the actual ticket details before sending.

Thank you for your patience.

Support Team''',
            'body_html': '<p>HTML version of the support email</p>',
            'status': 'PENDING',
            'risk_score': 45,
            'keywords_matched': 'support,ticket,update'
        },
        {
            'message_id': f'manual_test_3_{datetime.now().timestamp()}@test.com',
            'sender': 'marketing@company.com',
            'recipients': 'subscribers@list.com',
            'subject': 'Special Announcement - Action Required',
            'body_text': '''Dear Valued Customer,

We have an important announcement to share with you.

[THIS SECTION NEEDS TO BE EDITED WITH ACTUAL CONTENT]

- Point 1: [EDIT]
- Point 2: [EDIT]
- Point 3: [EDIT]

Call to Action: [EDIT THIS BEFORE SENDING]

Best regards,
Marketing Team''',
            'body_html': '<p>HTML version of marketing email</p>',
            'status': 'PENDING',
            'risk_score': 80,
            'keywords_matched': 'announcement,action,marketing'
        }
    ]

    created_ids = []
    for email in test_emails:
        cursor.execute("""
            INSERT INTO email_messages (
                message_id, sender, recipients, subject, body_text, body_html,
                status, risk_score, keywords_matched, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email['message_id'],
            email['sender'],
            email['recipients'],
            email['subject'],
            email['body_text'],
            email['body_html'],
            email['status'],
            email['risk_score'],
            email['keywords_matched'],
            datetime.now().isoformat()
        ))
        created_ids.append(cursor.lastrowid)
        print(f"✓ Created test email ID {cursor.lastrowid}:")
        print(f"  From: {email['sender']}")
        print(f"  Subject: {email['subject']}")
        print(f"  Risk Score: {email['risk_score']}")
        print()

    conn.commit()
    conn.close()

    print("="*60)
    print("TEST EMAILS CREATED SUCCESSFULLY")
    print("="*60)
    print("\nTo test the edit functionality:")
    print("1. Open http://localhost:5000 in your browser")
    print("2. Login with admin/admin123")
    print("3. Go to the 'Emails' tab")
    print("4. You should see 3 new PENDING emails")
    print("5. Click the Edit button (pencil icon) on any email")
    print("6. The edit modal should open with the email content")
    print("7. Edit the subject and body as needed")
    print("8. Click 'Save Changes'")
    print("9. Verify the changes are saved")
    print("\nCreated email IDs:", created_ids)

if __name__ == "__main__":
    create_test_email()