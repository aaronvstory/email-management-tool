"""
Flask Web Application for Email Moderation Dashboard
"""
import os
import json
import sqlite3
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from email import message_from_bytes, policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import configparser
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Load configuration
config = configparser.ConfigParser()
config.read('config/config.ini')

DB_PATH = 'data/email_moderation.db'

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_action(message_id, action, user, details="", ip_address=""):
    """Log action to audit trail"""
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO audit_logs (message_id, action, user, details, ip_address)
        VALUES (?, ?, ?, ?, ?)
    """, (message_id, action, user, details, ip_address))
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    """Main dashboard showing email queue statistics"""
    conn = get_db_connection()

    # Get queue statistics
    stats = {}
    stats['total'] = conn.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]
    stats['pending'] = conn.execute('SELECT COUNT(*) FROM email_messages WHERE status = "PENDING"').fetchone()[0]
    stats['approved'] = conn.execute('SELECT COUNT(*) FROM email_messages WHERE status = "APPROVED"').fetchone()[0]
    stats['rejected'] = conn.execute('SELECT COUNT(*) FROM email_messages WHERE status = "REJECTED"').fetchone()[0]
    stats['sent'] = conn.execute('SELECT COUNT(*) FROM email_messages WHERE status = "SENT"').fetchone()[0]

    # Get recent messages
    recent_messages = conn.execute("""
        SELECT message_id, sender, recipients, subject, status, created_at, keywords_matched
        FROM email_messages 
        ORDER BY created_at DESC 
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template('dashboard.html', stats=stats, recent_messages=recent_messages)

@app.route('/queue')
def queue():
    """Email moderation queue"""
    status_filter = request.args.get('status', 'PENDING')

    conn = get_db_connection()

    if status_filter == 'ALL':
        messages = conn.execute("""
            SELECT * FROM email_messages 
            ORDER BY created_at DESC
        """).fetchall()
    else:
        messages = conn.execute("""
            SELECT * FROM email_messages 
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status_filter,)).fetchall()

    conn.close()

    return render_template('queue.html', messages=messages, current_filter=status_filter)

@app.route('/message/<message_id>')
def view_message(message_id):
    """View individual message details"""
    conn = get_db_connection()

    message_row = conn.execute("""
        SELECT * FROM email_messages WHERE message_id = ?
    """, (message_id,)).fetchone()

    if not message_row:
        flash('Message not found', 'error')
        return redirect(url_for('queue'))

    # Parse the email content
    try:
        email_msg = message_from_bytes(message_row['raw_content'], policy=policy.default)

        # Extract email parts
        email_data = {
            'message_id': message_row['message_id'],
            'sender': message_row['sender'],
            'recipients': json.loads(message_row['recipients']),
            'subject': email_msg.get('Subject', 'No Subject'),
            'date': email_msg.get('Date', ''),
            'status': message_row['status'],
            'keywords_matched': json.loads(message_row['keywords_matched'] or '[]'),
            'body_text': extract_body_text(email_msg),
            'body_html': extract_body_html(email_msg),
            'attachments': get_attachments_info(email_msg)
        }

    except Exception as e:
        logger.error(f"Error parsing email {message_id}: {e}")
        email_data = {
            'message_id': message_id,
            'error': 'Unable to parse email content'
        }

    conn.close()

    return render_template('message_detail.html', email=email_data)

@app.route('/message/<message_id>/edit')
def edit_message(message_id):
    """Edit message content"""
    conn = get_db_connection()

    message_row = conn.execute("""
        SELECT * FROM email_messages WHERE message_id = ?
    """, (message_id,)).fetchone()

    if not message_row:
        flash('Message not found', 'error')
        return redirect(url_for('queue'))

    # Parse the email content
    email_msg = message_from_bytes(message_row['raw_content'], policy=policy.default)

    email_data = {
        'message_id': message_id,
        'sender': message_row['sender'],
        'recipients': json.loads(message_row['recipients']),
        'subject': email_msg.get('Subject', 'No Subject'),
        'body_text': extract_body_text(email_msg),
        'body_html': extract_body_html(email_msg),
        'status': message_row['status']
    }

    conn.close()

    return render_template('message_edit.html', email=email_data)

@app.route('/message/<message_id>/update', methods=['POST'])
def update_message(message_id):
    """Update message content"""
    new_subject = request.form.get('subject')
    new_body = request.form.get('body')
    reviewer_name = request.form.get('reviewer_name', 'Anonymous')

    # Add "Checked by" stamp
    verification_stamp = f"\n\n--- CHECKED BY {reviewer_name.upper()} - APPROVED ---\n"
    new_body_with_stamp = new_body + verification_stamp

    conn = get_db_connection()

    # Get original message
    message_row = conn.execute("""
        SELECT raw_content FROM email_messages WHERE message_id = ?
    """, (message_id,)).fetchone()

    if message_row:
        # Create modified email
        original_msg = message_from_bytes(message_row['raw_content'], policy=policy.default)

        # Create new message with modifications
        new_msg = MIMEText(new_body_with_stamp)
        new_msg['Subject'] = new_subject
        new_msg['From'] = original_msg.get('From')
        new_msg['To'] = original_msg.get('To')
        new_msg['Date'] = original_msg.get('Date')

        # Store processed content
        conn.execute("""
            UPDATE email_messages 
            SET processed_content = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE message_id = ?
        """, (new_msg.as_bytes(), reviewer_name, message_id))

        conn.commit()

        # Log the modification
        log_action(message_id, 'MESSAGE_MODIFIED', reviewer_name, 
                  f"Subject: {new_subject}, Body modified")

        flash('Message updated successfully', 'success')

    conn.close()

    return redirect(url_for('view_message', message_id=message_id))

def extract_body_text(email_msg):
    """Extract plain text body from email"""
    body = ""
    try:
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            if email_msg.get_content_type() == "text/plain":
                body = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error extracting text body: {e}")
    return body

def extract_body_html(email_msg):
    """Extract HTML body from email"""
    body = ""
    try:
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/html":
                    body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            if email_msg.get_content_type() == "text/html":
                body = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error extracting HTML body: {e}")
    return body

def get_attachments_info(email_msg):
    """Get attachment information"""
    attachments = []
    try:
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_filename():
                    attachments.append({
                        'filename': part.get_filename(),
                        'content_type': part.get_content_type(),
                        'size': len(part.get_payload(decode=True) or b'')
                    })
    except Exception as e:
        logger.error(f"Error getting attachment info: {e}")
    return attachments

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
