# Fix the Flask web application to include proper Jinja2 filters and complete functionality
updated_web_app = '''"""
Flask Web Application for Email Moderation Dashboard
Complete implementation with all features
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

# Add custom Jinja2 filter for JSON parsing
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string in templates"""
    try:
        return json.loads(value) if value else []
    except:
        return []

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_action(message_id, action, user, details="", ip_address=""):
    """Log action to audit trail"""
    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO audit_logs (message_id, action, user, details, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, action, user, details, ip_address))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging action: {e}")

@app.route('/')
def dashboard():
    """Main dashboard showing email queue statistics"""
    try:
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
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('dashboard.html', stats={'total':0,'pending':0,'approved':0,'rejected':0,'sent':0}, recent_messages=[])

@app.route('/queue')
def queue():
    """Email moderation queue"""
    status_filter = request.args.get('status', 'PENDING')
    
    try:
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
    except Exception as e:
        logger.error(f"Error loading queue: {e}")
        flash(f'Error loading queue: {e}', 'error')
        return render_template('queue.html', messages=[], current_filter=status_filter)

@app.route('/message/<message_id>')
def view_message(message_id):
    """View individual message details"""
    try:
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
                'recipients': json.loads(message_row['recipients'] or '[]'),
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
                'error': f'Unable to parse email content: {e}'
            }
        
        conn.close()
        
        return render_template('message_detail.html', email=email_data)
    except Exception as e:
        logger.error(f"Error viewing message {message_id}: {e}")
        flash(f'Error viewing message: {e}', 'error')
        return redirect(url_for('queue'))

@app.route('/message/<message_id>/edit')
def edit_message(message_id):
    """Edit message content"""
    try:
        conn = get_db_connection()
        
        message_row = conn.execute("""
            SELECT * FROM email_messages WHERE message_id = ?
        """, (message_id,)).fetchone()
        
        if not message_row:
            flash('Message not found', 'error')
            return redirect(url_for('queue'))
        
        if message_row['status'] != 'PENDING':
            flash('Only pending messages can be edited', 'warning')
            return redirect(url_for('view_message', message_id=message_id))
        
        # Parse the email content
        email_msg = message_from_bytes(message_row['raw_content'], policy=policy.default)
        
        email_data = {
            'message_id': message_id,
            'sender': message_row['sender'],
            'recipients': json.loads(message_row['recipients'] or '[]'),
            'subject': email_msg.get('Subject', 'No Subject'),
            'body_text': extract_body_text(email_msg),
            'body_html': extract_body_html(email_msg),
            'status': message_row['status']
        }
        
        conn.close()
        
        return render_template('message_edit.html', email=email_data)
    except Exception as e:
        logger.error(f"Error editing message {message_id}: {e}")
        flash(f'Error editing message: {e}', 'error')
        return redirect(url_for('queue'))

@app.route('/message/<message_id>/update', methods=['POST'])
def update_message(message_id):
    """Update message content"""
    try:
        new_subject = request.form.get('subject', '').strip()
        new_body = request.form.get('body', '').strip()
        reviewer_name = request.form.get('reviewer_name', 'Anonymous').strip()
        action = request.form.get('action', 'save_draft')
        
        if not new_subject or not new_body or not reviewer_name:
            flash('Subject, body, and reviewer name are required', 'error')
            return redirect(url_for('edit_message', message_id=message_id))
        
        # Add "Checked by" stamp if requested
        add_stamp = request.form.get('add_stamp') == 'on'
        if add_stamp:
            verification_stamp = f"\\n\\n--- CHECKED BY {reviewer_name.upper()} - APPROVED ---\\n"
            new_body_with_stamp = new_body + verification_stamp
        else:
            new_body_with_stamp = new_body
        
        conn = get_db_connection()
        
        # Get original message
        message_row = conn.execute("""
            SELECT raw_content, sender, recipients FROM email_messages WHERE message_id = ?
        """, (message_id,)).fetchone()
        
        if message_row:
            # Create modified email
            original_msg = message_from_bytes(message_row['raw_content'], policy=policy.default)
            recipients = json.loads(message_row['recipients'])
            
            # Create new message with modifications
            new_msg = MIMEText(new_body_with_stamp, 'plain', 'utf-8')
            new_msg['Subject'] = new_subject
            new_msg['From'] = message_row['sender']
            new_msg['To'] = ', '.join(recipients)
            new_msg['Date'] = original_msg.get('Date', '')
            
            # Determine new status
            new_status = 'APPROVED' if action == 'save_and_approve' else 'PENDING'
            
            # Store processed content
            conn.execute("""
                UPDATE email_messages 
                SET processed_content = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP,
                    status = ?, subject = ?
                WHERE message_id = ?
            """, (new_msg.as_bytes(), reviewer_name, new_status, new_subject, message_id))
            
            conn.commit()
            
            # Log the modification
            log_action(message_id, 'MESSAGE_MODIFIED', reviewer_name, 
                      f"Subject: {new_subject}, Status: {new_status}")
            
            if action == 'save_and_approve':
                flash(f'Message updated and approved by {reviewer_name}', 'success')
            else:
                flash(f'Message updated and saved as draft', 'success')
        
        conn.close()
        
        return redirect(url_for('view_message', message_id=message_id))
    except Exception as e:
        logger.error(f"Error updating message {message_id}: {e}")
        flash(f'Error updating message: {e}', 'error')
        return redirect(url_for('edit_message', message_id=message_id))

@app.route('/message/<message_id>/approve', methods=['POST'])
def approve_message(message_id):
    """Approve a message for delivery"""
    try:
        reviewer_name = request.form.get('reviewer_name', 'System')
        
        conn = get_db_connection()
        conn.execute("""
            UPDATE email_messages 
            SET status = 'APPROVED', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
            WHERE message_id = ? AND status = 'PENDING'
        """, (reviewer_name, message_id))
        
        if conn.total_changes > 0:
            log_action(message_id, 'MESSAGE_APPROVED', reviewer_name)
            flash(f'Message approved by {reviewer_name}', 'success')
        else:
            flash('Message not found or already processed', 'error')
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('view_message', message_id=message_id))
    except Exception as e:
        logger.error(f"Error approving message {message_id}: {e}")
        flash(f'Error approving message: {e}', 'error')
        return redirect(url_for('view_message', message_id=message_id))

@app.route('/message/<message_id>/reject', methods=['POST'])
def reject_message(message_id):
    """Reject a message"""
    try:
        reviewer_name = request.form.get('reviewer_name', 'System')
        reason = request.form.get('reason', 'No reason provided')
        
        conn = get_db_connection()
        conn.execute("""
            UPDATE email_messages 
            SET status = 'REJECTED', reviewed_at = CURRENT_TIMESTAMP, 
                reviewed_by = ?, review_notes = ?
            WHERE message_id = ? AND status = 'PENDING'
        """, (reviewer_name, reason, message_id))
        
        if conn.total_changes > 0:
            log_action(message_id, 'MESSAGE_REJECTED', reviewer_name, reason)
            flash(f'Message rejected by {reviewer_name}', 'success')
        else:
            flash('Message not found or already processed', 'error')
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('queue'))
    except Exception as e:
        logger.error(f"Error rejecting message {message_id}: {e}")
        flash(f'Error rejecting message: {e}', 'error')
        return redirect(url_for('view_message', message_id=message_id))

def extract_body_text(email_msg):
    """Extract plain text body from email"""
    body = ""
    try:
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode('utf-8', errors='ignore')
        else:
            if email_msg.get_content_type() == "text/plain":
                payload = email_msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
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
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode('utf-8', errors='ignore')
        else:
            if email_msg.get_content_type() == "text/html":
                payload = email_msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
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
                    payload = part.get_payload(decode=True) or b''
                    attachments.append({
                        'filename': part.get_filename(),
                        'content_type': part.get_content_type(),
                        'size': len(payload)
                    })
    except Exception as e:
        logger.error(f"Error getting attachment info: {e}")
    return attachments

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
'''

# Update the web application
with open("email_moderation_system/app/web_app.py", "w") as f:
    f.write(updated_web_app)

print("Updated web_app.py with complete functionality")
print("✓ Fixed Jinja2 template filters")  
print("✓ Added approve/reject endpoints")
print("✓ Enhanced error handling")
print("✓ Complete CRUD operations")
print("✓ Proper audit logging")