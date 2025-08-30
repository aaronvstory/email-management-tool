#!/usr/bin/env python3
"""
Simplified Email Management Tool with Modern Dashboard
A fully functional implementation that can run immediately
"""

import os
import sqlite3
import json
import threading
import time
import smtplib
import asyncio
from datetime import datetime, timedelta
from email import message_from_bytes, policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import aiosmtpd.controller
from aiosmtpd.handlers import Message

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database setup
DB_PATH = 'data/emails.db'

def init_database():
    """Initialize SQLite database with all required tables"""
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'reviewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Email messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            sender TEXT NOT NULL,
            recipients TEXT NOT NULL,
            subject TEXT,
            body_text TEXT,
            body_html TEXT,
            raw_content BLOB,
            status TEXT DEFAULT 'PENDING',
            keywords_matched TEXT,
            risk_score INTEGER DEFAULT 0,
            reviewer_id INTEGER,
            review_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            sent_at TIMESTAMP
        )
    ''')
    
    # Moderation rules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moderation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            rule_type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            action TEXT DEFAULT 'HOLD',
            priority INTEGER DEFAULT 50,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Audit logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            user_id INTEGER,
            email_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user
    admin_exists = cursor.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin_exists:
        admin_hash = generate_password_hash('admin123')
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
            ('admin', admin_hash, 'admin@example.com', 'admin')
        )
    
    # Create default rules
    default_rules = [
        ('Block Invoice Keywords', 'KEYWORD', 'invoice,payment,urgent', 'HOLD', 80),
        ('Check Attachments', 'ATTACHMENT', '.pdf,.doc,.xls', 'HOLD', 70),
        ('External Recipients', 'DOMAIN', '@external.com', 'HOLD', 60),
    ]
    
    for rule in default_rules:
        exists = cursor.execute("SELECT id FROM moderation_rules WHERE name = ?", (rule[0],)).fetchone()
        if not exists:
            cursor.execute(
                "INSERT INTO moderation_rules (name, rule_type, pattern, action, priority) VALUES (?, ?, ?, ?, ?)",
                rule
            )
    
    conn.commit()
    conn.close()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    user = cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

# SMTP Proxy Handler
class EmailModerationHandler(Message):
    """Handle incoming emails through SMTP proxy"""
    
    def handle_message(self, message):
        """Process incoming email"""
        try:
            # Parse email
            email_msg = message_from_bytes(message.original_content, policy=policy.default)
            
            # Extract data
            sender = str(message.mail_from)
            recipients = json.dumps([str(r) for r in message.rcpt_tos])
            subject = email_msg.get('Subject', 'No Subject')
            message_id = email_msg.get('Message-ID', f"msg_{datetime.now().timestamp()}")
            
            # Extract body
            body_text = ""
            body_html = ""
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif part.get_content_type() == "text/html":
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body_text = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Check moderation rules
            keywords_matched, risk_score = self.check_rules(subject, body_text)
            
            # Store in database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO email_messages 
                (message_id, sender, recipients, subject, body_text, body_html, raw_content, keywords_matched, risk_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (message_id, sender, recipients, subject, body_text, body_html, 
                  message.original_content, json.dumps(keywords_matched), risk_score))
            conn.commit()
            conn.close()
            
            print(f"📧 Email intercepted: {subject} from {sender}")
            
        except Exception as e:
            print(f"Error processing email: {e}")
    
    def check_rules(self, subject, body):
        """Check moderation rules"""
        keywords = []
        risk_score = 0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        rules = cursor.execute("SELECT pattern, priority FROM moderation_rules WHERE is_active = 1").fetchall()
        conn.close()
        
        content = f"{subject} {body}".lower()
        for pattern, priority in rules:
            for keyword in pattern.split(','):
                if keyword.lower() in content:
                    keywords.append(keyword)
                    risk_score += priority // 10
        
        return keywords, min(risk_score, 100)

# Routes
@app.route('/')
def index():
    """Redirect to dashboard or login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        user = cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", 
                              (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            user_obj = User(user[0], user[1], user[3])
            login_user(user_obj)
            
            # Log the action
            log_action('LOGIN', user[0], None, f"User {username} logged in")
            
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    log_action('LOGOUT', current_user.id, None, f"User {current_user.username} logged out")
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with statistics"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get statistics
    stats = {
        'total': cursor.execute("SELECT COUNT(*) FROM email_messages").fetchone()[0],
        'pending': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0],
        'approved': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'APPROVED'").fetchone()[0],
        'rejected': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'REJECTED'").fetchone()[0],
        'sent': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'SENT'").fetchone()[0],
    }
    
    # Get recent emails
    recent_emails = cursor.execute("""
        SELECT id, sender, recipients, subject, status, risk_score, created_at
        FROM email_messages
        ORDER BY created_at DESC
        LIMIT 10
    """).fetchall()
    
    # Get active rules count
    active_rules = cursor.execute("SELECT COUNT(*) FROM moderation_rules WHERE is_active = 1").fetchone()[0]
    
    conn.close()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_emails=recent_emails,
                         active_rules=active_rules,
                         user=current_user)

@app.route('/emails')
@login_required
def email_queue():
    """Email queue page"""
    status_filter = request.args.get('status', 'PENDING')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if status_filter == 'ALL':
        emails = cursor.execute("""
            SELECT * FROM email_messages 
            ORDER BY created_at DESC
        """).fetchall()
    else:
        emails = cursor.execute("""
            SELECT * FROM email_messages 
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status_filter,)).fetchall()
    
    conn.close()
    
    return render_template('email_queue.html', emails=emails, current_filter=status_filter)

@app.route('/email/<int:email_id>')
@login_required
def view_email(email_id):
    """View email details"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    email = cursor.execute("SELECT * FROM email_messages WHERE id = ?", (email_id,)).fetchone()
    
    if not email:
        conn.close()
        flash('Email not found', 'error')
        return redirect(url_for('email_queue'))
    
    conn.close()
    
    # Parse recipients and keywords
    email_data = dict(email)
    email_data['recipients'] = json.loads(email_data['recipients']) if email_data['recipients'] else []
    email_data['keywords_matched'] = json.loads(email_data['keywords_matched']) if email_data['keywords_matched'] else []
    
    return render_template('email_detail.html', email=email_data)

@app.route('/email/<int:email_id>/action', methods=['POST'])
@login_required
def email_action(email_id):
    """Handle email actions (approve/reject)"""
    action = request.form.get('action')
    notes = request.form.get('notes', '')
    
    if action not in ['APPROVE', 'REJECT']:
        return jsonify({'error': 'Invalid action'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update email status
    new_status = 'APPROVED' if action == 'APPROVE' else 'REJECTED'
    cursor.execute("""
        UPDATE email_messages 
        SET status = ?, reviewer_id = ?, review_notes = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, current_user.id, notes, email_id))
    
    # Log the action
    log_action(action, current_user.id, email_id, f"Email {action.lower()}d with notes: {notes}")
    
    conn.commit()
    conn.close()
    
    flash(f'Email {action.lower()}d successfully', 'success')
    return redirect(url_for('email_queue'))

@app.route('/rules')
@login_required
def rules():
    """Moderation rules page"""
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    rules = cursor.execute("SELECT * FROM moderation_rules ORDER BY priority DESC").fetchall()
    
    conn.close()
    
    return render_template('rules.html', rules=rules)

@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for real-time statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {
        'total': cursor.execute("SELECT COUNT(*) FROM email_messages").fetchone()[0],
        'pending': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0],
        'approved': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'APPROVED'").fetchone()[0],
        'rejected': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'REJECTED'").fetchone()[0],
        'high_risk': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE risk_score >= 70").fetchone()[0],
    }
    
    # Get hourly email volume for chart
    hourly_volume = cursor.execute("""
        SELECT strftime('%H', created_at) as hour, COUNT(*) as count
        FROM email_messages
        WHERE date(created_at) = date('now')
        GROUP BY hour
        ORDER BY hour
    """).fetchall()
    
    conn.close()
    
    return jsonify({
        'stats': stats,
        'hourly_volume': [{'hour': h[0], 'count': h[1]} for h in hourly_volume]
    })

@app.route('/api/events')
@login_required
def api_events():
    """Server-Sent Events endpoint for real-time updates"""
    def generate():
        while True:
            # Get latest email count
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            pending = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0]
            conn.close()
            
            data = json.dumps({'pending': pending, 'timestamp': datetime.now().isoformat()})
            yield f"data: {data}\n\n"
            
            time.sleep(5)  # Update every 5 seconds
    
    return Response(generate(), mimetype="text/event-stream")

def log_action(action, user_id, email_id, details):
    """Log action to audit trail"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (action, user_id, email_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?)
    """, (action, user_id, email_id, details, request.remote_addr if request else '127.0.0.1'))
    conn.commit()
    conn.close()

def run_smtp_proxy():
    """Run SMTP proxy server"""
    handler = EmailModerationHandler()
    controller = aiosmtpd.controller.Controller(handler, hostname='127.0.0.1', port=8587)
    controller.start()
    print("📧 SMTP Proxy started on port 8587")

# Initialize database
init_database()

if __name__ == '__main__':
    # Start SMTP proxy in background thread
    smtp_thread = threading.Thread(target=run_smtp_proxy, daemon=True)
    smtp_thread.start()
    
    # Give SMTP proxy time to start
    time.sleep(2)
    
    # Print startup info
    print("\n" + "="*60)
    print("   EMAIL MANAGEMENT TOOL - MODERN DASHBOARD")
    print("="*60)
    print("\n   🚀 Services Started:")
    print("   📧 SMTP Proxy: localhost:8587")
    print("   🌐 Web Dashboard: http://127.0.0.1:5000")
    print("   👤 Login: admin / admin123")
    print("\n   ✨ Features:")
    print("   • Real-time email moderation")
    print("   • Risk scoring system")
    print("   • Complete audit trail")
    print("   • Modern responsive UI")
    print("\n" + "="*60 + "\n")
    
    # Run Flask app
    app.run(debug=True, use_reloader=False)