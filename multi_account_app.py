#!/usr/bin/env python3
"""
Enhanced Email Management Tool with Multi-Account Support
Full dashboard with account management, diagnostics, and interception
"""

import os
import sqlite3
import json
import threading
import time
import smtplib
import imaplib
import ssl
import asyncio
import base64
from datetime import datetime, timedelta
from email import message_from_bytes, policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import aiosmtpd.controller

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')# Database setup
DB_PATH = 'data/emails.db'
ACCOUNTS_FILE = 'email_accounts.json'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Global variable to store email accounts
EMAIL_ACCOUNTS = {}

def load_email_accounts():
    """Load email accounts from JSON file"""
    global EMAIL_ACCOUNTS
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            data = json.load(f)
            EMAIL_ACCOUNTS = {acc['id']: acc for acc in data['accounts']}
            print(f"✅ Loaded {len(EMAIL_ACCOUNTS)} email accounts")
    except FileNotFoundError:
        print("⚠️ No accounts file found, creating default...")
        EMAIL_ACCOUNTS = {}
    except Exception as e:
        print(f"❌ Error loading accounts: {e}")
        EMAIL_ACCOUNTS = {}

def save_email_accounts():
    """Save email accounts to JSON file"""
    try:
        accounts_list = list(EMAIL_ACCOUNTS.values())
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump({'accounts': accounts_list}, f, indent=2)
        print(f"✅ Saved {len(accounts_list)} email accounts")
    except Exception as e:
        print(f"❌ Error saving accounts: {e}")

def init_database():
    """Initialize database with enhanced schema for multi-account support"""
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # Enhanced emails table with account_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            body TEXT,
            headers TEXT,
            status TEXT DEFAULT 'PENDING',
            risk_score INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            approved_by TEXT,
            rejected_by TEXT,
            approved_at DATETIME,
            rejected_at DATETIME,
            notes TEXT,
            modified BOOLEAN DEFAULT 0,
            modified_body TEXT
        )
    ''')
    
    # Account diagnostics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            test_type TEXT,
            status TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with multi-account support")# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], bool(user_data[2]))
    return None

def test_email_account(account):
    """Test email account connectivity"""
    results = {
        'smtp': {'status': 'pending', 'message': ''},
        'imap': {'status': 'pending', 'message': ''}
    }
    
    # Test SMTP
    try:
        if account['smtp']['use_ssl']:
            server = smtplib.SMTP_SSL(account['smtp']['host'], account['smtp']['port'], timeout=10)
        else:
            server = smtplib.SMTP(account['smtp']['host'], account['smtp']['port'], timeout=10)
            if account['smtp']['use_tls']:
                server.starttls()
        server.login(account['smtp']['username'], account['smtp']['password'])
        server.quit()
        results['smtp'] = {'status': 'success', 'message': 'SMTP connection successful'}
    except Exception as e:
        results['smtp'] = {'status': 'error', 'message': str(e)}
    
    # Test IMAP
    try:
        if account['imap']['use_ssl']:
            imap = imaplib.IMAP4_SSL(account['imap']['host'], account['imap']['port'])
        else:
            imap = imaplib.IMAP4(account['imap']['host'], account['imap']['port'])
        
        imap.login(account['imap']['username'], account['imap']['password'])
        imap.select('INBOX')
        imap.close()
        imap.logout()
        results['imap'] = {'status': 'success', 'message': 'IMAP connection successful'}
    except Exception as e:
        results['imap'] = {'status': 'error', 'message': str(e)}
    
    # Save diagnostics
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO account_diagnostics (account_id, test_type, status, message)
        VALUES (?, ?, ?, ?)
    ''', (account['id'], 'connectivity', json.dumps(results), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return results# Enhanced SMTP Handler for Multi-Account Interception
class MultiAccountEmailHandler:
    """Handle incoming emails through SMTP proxy with multi-account support"""
    
    async def handle_DATA(self, server, session, envelope):
        """Process incoming email and determine which account it belongs to"""
        print(f"📨 Intercepted: {envelope.mail_from} → {envelope.rcpt_tos}")
        
        # Determine which account this email is for
        account_id = None
        for acc_id, account in EMAIL_ACCOUNTS.items():
            if account['email'] in envelope.rcpt_tos or account['email'] == envelope.mail_from:
                account_id = acc_id
                break
        
        if not account_id:
            # Default to first active account
            for acc_id, account in EMAIL_ACCOUNTS.items():
                if account.get('active', False):
                    account_id = acc_id
                    break
        
        # Parse email content
        try:
            msg = message_from_bytes(envelope.content, policy=policy.default)
            subject = msg.get('Subject', 'No Subject')
            body = self.get_email_body(msg)
            headers = json.dumps(dict(msg.items()))
        except Exception as e:
            subject = "Parse Error"
            body = f"Error parsing email: {str(e)}"
            headers = "{}"        
        # Calculate risk score
        risk_score = self.calculate_risk_score(subject, body)
        
        # Store in database with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10.0)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO emails (account_id, sender, recipient, subject, body, headers, risk_score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account_id,
                    envelope.mail_from,
                    ', '.join(envelope.rcpt_tos),
                    subject,
                    body,
                    headers,
                    risk_score,
                    'PENDING'
                ))
                conn.commit()
                conn.close()
                print(f"✅ Email stored for account: {account_id}")
                break
            except sqlite3.OperationalError as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    print(f"❌ Database error after {max_retries} attempts: {e}")
        
        return '250 Message accepted for delivery'    
    def get_email_body(self, msg):
        """Extract email body from message"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif part.get_content_type() == "text/html":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ""
    
    def calculate_risk_score(self, subject, body):
        """Calculate risk score based on keywords"""
        risk_keywords = {
            'urgent': 20, 'payment': 30, 'invoice': 25, 'password': 40,
            'account': 15, 'suspended': 35, 'verify': 25, 'click here': 30,
            'act now': 25, 'limited time': 20, 'bitcoin': 45, 'wire transfer': 40
        }
        
        score = 0
        content = (subject + " " + body).lower()
        
        for keyword, value in risk_keywords.items():
            if keyword in content:
                score += value
        
        return min(score, 100)  # Cap at 100

# Flask Routes
@app.route('/')
def index():
    return redirect(url_for('dashboard'))@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], bool(user_data[3]))
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()    
    # Get email statistics per account
    stats = {}
    for account_id in EMAIL_ACCOUNTS:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                AVG(risk_score) as avg_risk
            FROM emails 
            WHERE account_id = ?
        ''', (account_id,))
        result = cursor.fetchone()
        stats[account_id] = {
            'total': result[0] or 0,
            'pending': result[1] or 0,
            'approved': result[2] or 0,
            'rejected': result[3] or 0,
            'avg_risk': round(result[4] or 0, 1)
        }
    
    conn.close()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         accounts=EMAIL_ACCOUNTS,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/accounts')
@login_required
def accounts():
    """Account management page"""
    return render_template('accounts.html', accounts=EMAIL_ACCOUNTS)

@app.route('/api/accounts', methods=['GET'])
@login_required
def get_accounts():
    """API endpoint to get all accounts"""
    return jsonify(list(EMAIL_ACCOUNTS.values()))

@app.route('/api/accounts', methods=['POST'])
@login_required
def add_account():
    """Add new email account"""
    data = request.json
    account_id = data.get('id', f"{data['provider']}_{data['email'].split('@')[0]}")
    
    EMAIL_ACCOUNTS[account_id] = {
        'id': account_id,
        'name': data['name'],
        'email': data['email'],
        'provider': data['provider'],
        'smtp': data['smtp'],
        'imap': data['imap'],
        'active': data.get('active', True),
        'interception_enabled': data.get('interception_enabled', True)
    }
    
    save_email_accounts()
    return jsonify({'success': True, 'account_id': account_id})

@app.route('/api/accounts/<account_id>', methods=['PUT'])
@login_required
def update_account(account_id):
    """Update email account"""
    if account_id not in EMAIL_ACCOUNTS:
        return jsonify({'error': 'Account not found'}), 404
    
    data = request.json
    EMAIL_ACCOUNTS[account_id].update(data)
    save_email_accounts()
    return jsonify({'success': True})

@app.route('/api/accounts/<account_id>', methods=['DELETE'])
@login_required
def delete_account(account_id):
    """Delete email account"""
    if account_id not in EMAIL_ACCOUNTS:
        return jsonify({'error': 'Account not found'}), 404
    
    del EMAIL_ACCOUNTS[account_id]
    save_email_accounts()
    return jsonify({'success': True})

@app.route('/api/accounts/<account_id>/test', methods=['POST'])
@login_required
def test_account(account_id):
    """Test account connectivity"""
    if account_id not in EMAIL_ACCOUNTS:
        return jsonify({'error': 'Account not found'}), 404
    
    results = test_email_account(EMAIL_ACCOUNTS[account_id])
    return jsonify(results)

@app.route('/api/accounts/import', methods=['POST'])
@login_required
def import_accounts():
    """Import accounts from JSON"""
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        data = json.load(file.stream)
        imported_count = 0
        
        for account in data.get('accounts', []):
            account_id = account.get('id', f"{account['provider']}_{account['email'].split('@')[0]}")
            EMAIL_ACCOUNTS[account_id] = account
            imported_count += 1
        
        save_email_accounts()
        return jsonify({'success': True, 'imported': imported_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/accounts/export', methods=['GET'])
@login_required
def export_accounts():
    """Export accounts to JSON"""
    accounts_data = {'accounts': list(EMAIL_ACCOUNTS.values())}
    return Response(
        json.dumps(accounts_data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=email_accounts.json'}
    )

@app.route('/emails')
@login_required
def emails():
    """Email management page"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get filter parameters
    account_filter = request.args.get('account', 'all')
    status_filter = request.args.get('status', 'all')
    
    # Build query
    query = "SELECT * FROM emails WHERE 1=1"
    params = []
    
    if account_filter != 'all':
        query += " AND account_id = ?"
        params.append(account_filter)
    
    if status_filter != 'all':
        query += " AND status = ?"
        params.append(status_filter)
    
    query += " ORDER BY timestamp DESC LIMIT 100"
    
    cursor.execute(query, params)
    emails = cursor.fetchall()
    conn.close()
    
    return render_template('emails.html', 
                         emails=emails, 
                         accounts=EMAIL_ACCOUNTS,
                         selected_account=account_filter,
                         selected_status=status_filter)@app.route('/api/emails/<int:email_id>', methods=['PUT'])
@login_required
def update_email(email_id):
    """Update email status or content"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    if 'status' in data:
        cursor.execute('''
            UPDATE emails 
            SET status = ?, approved_by = ?, approved_at = ?
            WHERE id = ?
        ''', (data['status'], current_user.username, datetime.now(), email_id))
    
    if 'body' in data:
        # Add modification timestamp
        modified_body = f"""
=== EMAIL INTERCEPTED AND MODIFIED ===
Modification Time: {datetime.now()}
Modified By: {current_user.username}
--- MODIFIED MESSAGE BELOW ---
{data['body']}
"""
        cursor.execute('''
            UPDATE emails 
            SET modified = 1, modified_body = ?
            WHERE id = ?
        ''', (modified_body, email_id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/diagnostics')
@login_required
def diagnostics():
    """Comprehensive diagnostics page for all accounts"""
    diagnostics_data = {}
    
    for account_id, account in EMAIL_ACCOUNTS.items():
        # Get latest diagnostic results
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT test_type, status, message, timestamp
            FROM account_diagnostics
            WHERE account_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (account_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            diagnostics_data[account_id] = {
                'last_test': result[3],
                'results': json.loads(result[1]) if result[1] else {}
            }
        else:
            diagnostics_data[account_id] = {
                'last_test': 'Never',
                'results': {}
            }    
    return render_template('diagnostics.html', 
                         accounts=EMAIL_ACCOUNTS,
                         diagnostics=diagnostics_data)

@app.route('/api/diagnostics/<account_id>/test', methods=['POST'])
@login_required
def run_diagnostic(account_id):
    """Run diagnostic test for specific account"""
    if account_id not in EMAIL_ACCOUNTS:
        return jsonify({'error': 'Account not found'}), 404
    
    results = test_email_account(EMAIL_ACCOUNTS[account_id])
    return jsonify(results)

@app.route('/api/stats')
@login_required
def get_stats():
    """Get real-time statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Overall stats
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected
        FROM emails    ''')
    overall = cursor.fetchone()
    
    # Per-account stats
    for account_id in EMAIL_ACCOUNTS:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                AVG(risk_score) as avg_risk
            FROM emails 
            WHERE account_id = ?
        ''', (account_id,))
        result = cursor.fetchone()
        stats[account_id] = {
            'total': result[0] or 0,
            'pending': result[1] or 0,
            'avg_risk': round(result[2] or 0, 1)
        }
    
    conn.close()
    
    return jsonify({
        'overall': {
            'total': overall[0] or 0,
            'pending': overall[1] or 0,
            'approved': overall[2] or 0,
            'rejected': overall[3] or 0
        },
        'accounts': stats,
        'timestamp': datetime.now().isoformat()
    })

def run_smtp_proxy():
    """Run SMTP proxy server in background"""
    async def start_proxy():
        handler = MultiAccountEmailHandler()
        controller = aiosmtpd.controller.Controller(
            handler,
            hostname='127.0.0.1',
            port=8587
        )
        controller.start()
        print(f"✅ SMTP Proxy running on port 8587")
        
        # Keep the thread alive
        while True:
            await asyncio.sleep(1)
    
    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_proxy())

def create_default_admin():
    """Create default admin user if none exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        password_hash = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (?, ?, ?)
        ''', ('admin', password_hash, True))
        conn.commit()
        print("✅ Default admin user created (admin/admin123)")
    
    conn.close()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 ENHANCED EMAIL MANAGEMENT TOOL WITH MULTI-ACCOUNT SUPPORT")
    print("="*60 + "\n")
    
    # Initialize everything
    init_database()
    load_email_accounts()
    create_default_admin()
    
    # Start SMTP proxy in background thread
    proxy_thread = threading.Thread(target=run_smtp_proxy, daemon=True)
    proxy_thread.start()
    
    # Start Flask app
    print(f"✅ Web Dashboard: http://localhost:5000")
    print(f"✅ SMTP Proxy: localhost:8587")
    print(f"✅ Login: admin / admin123")
    print("\n📧 Configure your email client to use localhost:8587 as SMTP server")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)