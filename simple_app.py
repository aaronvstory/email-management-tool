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

# Load environment variables
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import aiosmtpd.controller
# Removed Message import - using custom handler

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Database setup
DB_PATH = 'email_manager.db'

# Get or generate encryption key
def get_encryption_key():
    """Get or generate encryption key for passwords"""
    key_file = 'key.txt'
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key_content = f.read().strip()
            # Handle both plain key and key with prefix
            if b'Generated encryption key:' in key_content:
                key_content = key_content.split(b':')[-1].strip()
            return key_content
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Context processor to inject common variables into all templates
@app.context_processor
def inject_common_variables():
    """Make common variables available to all templates"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        pending_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0]
        conn.close()
    except:
        # If database doesn't exist yet or table is missing, return 0
        pending_count = 0
    return dict(pending_count=pending_count)

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
    
    # Email accounts table for managing monitored email accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT UNIQUE NOT NULL,
            email_address TEXT NOT NULL,
            imap_host TEXT NOT NULL,
            imap_port INTEGER DEFAULT 993,
            imap_username TEXT NOT NULL,
            imap_password TEXT NOT NULL,
            imap_use_ssl BOOLEAN DEFAULT 1,
            smtp_host TEXT NOT NULL,
            smtp_port INTEGER DEFAULT 465,
            smtp_username TEXT NOT NULL,
            smtp_password TEXT NOT NULL,
            smtp_use_ssl BOOLEAN DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            last_checked TIMESTAMP,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        exists = cursor.execute("SELECT id FROM moderation_rules WHERE rule_name = ?", (rule[0],)).fetchone()
        if not exists:
            cursor.execute(
                "INSERT INTO moderation_rules (rule_name, rule_type, condition_field, condition_operator, condition_value, action, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rule[0], 'keyword', 'body', 'contains', rule[2], rule[3], rule[4])
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

# Encryption setup for credentials
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', None)
if not ENCRYPTION_KEY:
    # Generate a new key if not provided
    ENCRYPTION_KEY = Fernet.generate_key()
    print(f"⚠️  No ENCRYPTION_KEY found. Generated new key (save this): {ENCRYPTION_KEY.decode()}")

cipher_suite = Fernet(ENCRYPTION_KEY if isinstance(ENCRYPTION_KEY, bytes) else ENCRYPTION_KEY.encode())

def encrypt_credential(plain_text):
    """Encrypt a credential"""
    if not plain_text:
        return None
    return cipher_suite.encrypt(plain_text.encode()).decode()

def decrypt_credential(encrypted_text):
    """Decrypt a credential"""
    if not encrypted_text:
        return None
    try:
        return cipher_suite.decrypt(encrypted_text.encode()).decode()
    except:
        return None

# IMAP monitoring threads
imap_threads = {}

def test_email_connection(account_type, host, port, username, password, use_ssl=True):
    """Test email connection (IMAP or SMTP)"""
    try:
        if account_type == 'imap':
            if use_ssl:
                imap = imaplib.IMAP4_SSL(host, port)
            else:
                imap = imaplib.IMAP4(host, port)
            imap.login(username, password)
            imap.logout()
            return True, "Connection successful"
        elif account_type == 'smtp':
            if use_ssl:
                context = ssl.create_default_context()
                smtp = smtplib.SMTP_SSL(host, port, context=context)
            else:
                smtp = smtplib.SMTP(host, port)
                smtp.starttls()
            smtp.login(username, password)
            smtp.quit()
            return True, "Connection successful"
    except Exception as e:
        return False, str(e)
    return False, "Unknown error"

def monitor_imap_account(account_id):
    """Monitor IMAP account for new emails"""
    app.logger.info(f"   📬 Started monitoring for account ID: {account_id}")
    
    while account_id in imap_threads:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row  # Enable dictionary access
            cursor = conn.cursor()
            account = cursor.execute("""
                SELECT * FROM email_accounts WHERE id = ? AND is_active = 1
            """, (account_id,)).fetchone()
            conn.close()
            
            if not account:
                break
                
            # Decrypt credentials
            imap_password = decrypt_credential(account['imap_password'])
            
            # Connect to IMAP - convert port to int
            imap_port = int(account['imap_port']) if account['imap_port'] else 993
            
            if account['imap_use_ssl']:
                imap = imaplib.IMAP4_SSL(account['imap_host'], imap_port)
            else:
                imap = imaplib.IMAP4(account['imap_host'], imap_port)
                
            imap.login(account['imap_username'], imap_password)
            imap.select('INBOX')
            
            # Search for unseen messages
            _, messages = imap.search(None, 'UNSEEN')
            
            for msg_id in messages[0].split():
                _, msg_data = imap.fetch(msg_id, '(RFC822)')
                email_body = msg_data[0][1]
                
                # Parse email
                msg = message_from_bytes(email_body, policy=policy.default)
                
                # Store in database for moderation
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO email_messages 
                    (message_id, sender, recipients, subject, body_text, raw_content, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
                ''', (
                    msg.get('Message-ID', ''),
                    msg.get('From', ''),
                    json.dumps([msg.get('To', '')]),
                    msg.get('Subject', ''),
                    msg.get_body(preferencelist=('plain',)).get_content() if msg.get_body(preferencelist=('plain',)) else '',
                    email_body
                ))
                conn.commit()
                conn.close()
                
                # Mark as seen (optional - you might want to keep as unseen until moderated)
                # imap.store(msg_id, '+FLAGS', '\\Seen')
            
            imap.logout()
            
            # Update last checked time
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_accounts SET last_checked = CURRENT_TIMESTAMP WHERE id = ?
            """, (account_id,))
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Log error
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_accounts SET last_error = ? WHERE id = ?
            """, (str(e), account_id))
            conn.commit()
            conn.close()
            
        # Wait before next check
        time.sleep(60)  # Check every minute

# SMTP Proxy Handler
class EmailModerationHandler:
    """Handle incoming emails through SMTP proxy"""
    
    async def handle_DATA(self, server, session, envelope):
        """Process incoming email"""
        print(f"📨 SMTP Handler: Received message from {envelope.mail_from} to {envelope.rcpt_tos}")
        try:
            # Parse email
            email_msg = message_from_bytes(envelope.content, policy=policy.default)
            print(f"📨 SMTP Handler: Parsed email successfully")
            
            # Extract data
            sender = str(envelope.mail_from)
            recipients = json.dumps([str(r) for r in envelope.rcpt_tos])
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
            
            # Store in database with retry logic
            print(f"📨 SMTP Handler: Storing in database - Subject: {subject}, Risk: {risk_score}")
            
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=10.0)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO email_messages 
                        (message_id, sender, recipients, subject, body_text, body_html, raw_content, keywords_matched, risk_score, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (message_id, sender, recipients, subject, body_text, body_html, 
                          envelope.content, json.dumps(keywords_matched), risk_score, 'PENDING'))
                    conn.commit()
                    print(f"📨 SMTP Handler: Database commit successful - Row ID: {cursor.lastrowid}")
                    conn.close()
                    break
                except sqlite3.OperationalError as e:
                    if "locked" in str(e) and attempt < max_retries - 1:
                        print(f"📨 SMTP Handler: Database locked, retrying... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(0.5)
                    else:
                        raise
            
            print(f"📧 Email intercepted: {subject} from {sender}")
            return '250 Message accepted for delivery'
            
        except Exception as e:
            print(f"Error processing email: {e}")
            import traceback
            traceback.print_exc()
            return f'500 Error: {e}'
    
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
@app.route('/dashboard/<tab>')
@login_required
def dashboard(tab='overview'):
    """Main dashboard with tab navigation"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get email accounts for account selector
    accounts = cursor.execute("""
        SELECT id, account_name, email_address, imap_host, imap_port, smtp_host, smtp_port,
               is_active, last_checked, last_error
        FROM email_accounts
        ORDER BY account_name
    """).fetchall()
    
    # Get selected account from query params
    selected_account_id = request.args.get('account_id', None)
    
    # Get statistics (filtered by account if selected)
    if selected_account_id:
        stats = {
            'total': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE account_id = ?", (selected_account_id,)).fetchone()[0],
            'pending': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING' AND account_id = ?", (selected_account_id,)).fetchone()[0],
            'approved': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'APPROVED' AND account_id = ?", (selected_account_id,)).fetchone()[0],
            'rejected': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'REJECTED' AND account_id = ?", (selected_account_id,)).fetchone()[0],
            'sent': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'SENT' AND account_id = ?", (selected_account_id,)).fetchone()[0],
        }
        
        # Get recent emails for selected account
        recent_emails = cursor.execute("""
            SELECT id, sender, recipients, subject, status, risk_score, created_at
            FROM email_messages
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (selected_account_id,)).fetchall()
    else:
        # Get overall statistics
        stats = {
            'total': cursor.execute("SELECT COUNT(*) FROM email_messages").fetchone()[0],
            'pending': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0],
            'approved': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'APPROVED'").fetchone()[0],
            'rejected': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'REJECTED'").fetchone()[0],
            'sent': cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'SENT'").fetchone()[0],
        }
        
        # Get recent emails from all accounts
        recent_emails = cursor.execute("""
            SELECT id, sender, recipients, subject, status, risk_score, created_at
            FROM email_messages
            ORDER BY created_at DESC
            LIMIT 10
        """).fetchall()
    
    # Get active rules count
    active_rules = cursor.execute("SELECT COUNT(*) FROM moderation_rules WHERE is_active = 1").fetchone()[0]
    
    conn.close()
    
    return render_template('dashboard_unified.html', 
                         stats=stats, 
                         recent_emails=recent_emails,
                         active_rules=active_rules,
                         accounts=accounts,
                         selected_account_id=selected_account_id,
                         active_tab=tab,
                         user=current_user)

@app.route('/test-dashboard')
@login_required
def test_dashboard():
    """Display the testing dashboard"""
    return render_template('test_dashboard.html')

@app.route('/test/cross-account', methods=['POST'])
@login_required
def run_cross_account_test():
    """Run cross-account email test"""
    try:
        import subprocess
        result = subprocess.run(['python', 'cross_account_test.py'], 
                              capture_output=True, text=True, timeout=60)
        
        # Parse the output to get test results
        output = result.stdout
        success = "TEST PASSED" in output
        
        return jsonify({
            'success': success,
            'output': output,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-status')
@login_required
def get_test_status():
    """Get current test status"""
    try:
        # Check for latest test results
        import glob
        test_files = glob.glob('test_results_*.json')
        if test_files:
            latest_file = max(test_files)
            with open(latest_file, 'r') as f:
                data = json.load(f)
                return jsonify(data)
        else:
            return jsonify({'status': 'No tests run yet'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/emails')
@login_required
def email_queue():
    """Email queue page"""
    status_filter = request.args.get('status', 'PENDING')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get counts for all statuses (always calculate these regardless of filter)
    pending_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0] or 0
    approved_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'APPROVED'").fetchone()[0] or 0
    rejected_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'REJECTED'").fetchone()[0] or 0
    total_count = cursor.execute("SELECT COUNT(*) FROM email_messages").fetchone()[0] or 0
    
    # Get filtered emails based on status
    if status_filter == 'ALL' or status_filter == 'all':
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
    
    # Debug: Print what we're passing to template
    app.logger.info(f"Passing to template - pending: {pending_count}, approved: {approved_count}, rejected: {rejected_count}, total: {total_count}")
    
    # Pass all counts to template
    return render_template('email_queue.html', 
                          emails=emails, 
                          current_filter=status_filter,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count,
                          total_count=total_count)

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
    try:
        email_data['recipients'] = json.loads(email_data['recipients']) if email_data['recipients'] else []
    except (json.JSONDecodeError, TypeError):
        # If not JSON, treat as comma-separated string
        if isinstance(email_data['recipients'], str):
            email_data['recipients'] = [r.strip() for r in email_data['recipients'].split(',') if r.strip()]
        else:
            email_data['recipients'] = []
    
    try:
        email_data['keywords_matched'] = json.loads(email_data['keywords_matched']) if email_data['keywords_matched'] else []
    except (json.JSONDecodeError, TypeError):
        # If not JSON, treat as comma-separated string
        if isinstance(email_data['keywords_matched'], str):
            email_data['keywords_matched'] = [k.strip() for k in email_data['keywords_matched'].split(',') if k.strip()]
        else:
            email_data['keywords_matched'] = []
    
    return render_template('email_detail.html', email=email_data)

@app.route('/email/<int:email_id>/action', methods=['POST'])
@login_required
def email_action(email_id):
    """Handle email actions (approve/reject)"""
    action = request.form.get('action', '').upper()
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

@app.route('/accounts')
@login_required
def email_accounts():
    """Email accounts management page with enhanced status monitoring"""
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get accounts with basic information (only columns that exist)
    accounts = cursor.execute("""
        SELECT id, account_name, email_address,
               imap_host, imap_port, imap_username, imap_use_ssl,
               smtp_host, smtp_port, smtp_username, smtp_use_ssl,
               is_active, last_checked, last_error,
               created_at, updated_at
        FROM email_accounts
        ORDER BY account_name
    """).fetchall()
    
    conn.close()
    
    # Check which template exists and use it
    import os
    template_path = os.path.join(app.template_folder, 'accounts_simple.html')
    if os.path.exists(template_path):
        return render_template('accounts_simple.html', accounts=accounts)
    else:
        # Convert list to dict for accounts.html compatibility
        accounts_dict = {acc['id']: dict(acc) for acc in accounts}
        return render_template('accounts.html', accounts=accounts_dict)

@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def add_email_account():
    """Add new email account"""
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Get form data
        account_name = request.form.get('account_name')
        email_address = request.form.get('email_address')
        
        # IMAP settings
        imap_host = request.form.get('imap_host')
        imap_port = int(request.form.get('imap_port', 993))
        imap_username = request.form.get('imap_username')
        imap_password = request.form.get('imap_password')
        imap_use_ssl = request.form.get('imap_use_ssl') == 'on'
        
        # SMTP settings
        smtp_host = request.form.get('smtp_host')
        smtp_port = int(request.form.get('smtp_port', 465))
        smtp_username = request.form.get('smtp_username')
        smtp_password = request.form.get('smtp_password')
        smtp_use_ssl = request.form.get('smtp_use_ssl') == 'on'
        
        # Test connections
        imap_success, imap_msg = test_email_connection('imap', imap_host, imap_port, imap_username, imap_password, imap_use_ssl)
        smtp_success, smtp_msg = test_email_connection('smtp', smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl)
        
        if not imap_success:
            flash(f'IMAP connection failed: {imap_msg}', 'error')
            return render_template('add_account.html')
        
        if not smtp_success:
            flash(f'SMTP connection failed: {smtp_msg}', 'error')
            return render_template('add_account.html')
        
        # Encrypt passwords
        encrypted_imap_password = encrypt_credential(imap_password)
        encrypted_smtp_password = encrypt_credential(smtp_password)
        
        # Save to database
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_accounts 
                (account_name, email_address, imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
                 smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (account_name, email_address, imap_host, imap_port, imap_username, encrypted_imap_password, imap_use_ssl,
                  smtp_host, smtp_port, smtp_username, encrypted_smtp_password, smtp_use_ssl))
            
            account_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Start IMAP monitoring thread
            thread = threading.Thread(target=monitor_imap_account, args=(account_id,), daemon=True)
            imap_threads[account_id] = thread
            thread.start()
            
            flash(f'Email account "{account_name}" added successfully!', 'success')
            return redirect(url_for('email_accounts'))
            
        except sqlite3.IntegrityError:
            flash('Account name already exists', 'error')
        except Exception as e:
            flash(f'Error adding account: {str(e)}', 'error')
    
    return render_template('add_account.html')

@app.route('/accounts/<int:account_id>/test')
@login_required
def test_account(account_id):
    """Test email account connection"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    account = cursor.execute("SELECT * FROM email_accounts WHERE id = ?", (account_id,)).fetchone()
    conn.close()
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Decrypt passwords
    imap_password = decrypt_credential(account[7])
    smtp_password = decrypt_credential(account[12])
    
    # Test IMAP
    imap_success, imap_msg = test_email_connection('imap', account[4], account[5], account[6], imap_password, account[8])
    
    # Test SMTP
    smtp_success, smtp_msg = test_email_connection('smtp', account[9], account[10], account[11], smtp_password, account[13])
    
    return jsonify({
        'imap': {'success': imap_success, 'message': imap_msg},
        'smtp': {'success': smtp_success, 'message': smtp_msg}
    })

@app.route('/accounts/<int:account_id>/toggle')
@login_required
def toggle_account(account_id):
    """Toggle account active status"""
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Toggle status
    cursor.execute("""
        UPDATE email_accounts 
        SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END 
        WHERE id = ?
    """, (account_id,))
    
    # Get new status
    is_active = cursor.execute("SELECT is_active FROM email_accounts WHERE id = ?", (account_id,)).fetchone()[0]
    
    conn.commit()
    conn.close()
    
    # Start or stop monitoring thread
    if is_active:
        if account_id not in imap_threads:
            thread = threading.Thread(target=monitor_imap_account, args=(account_id,), daemon=True)
            imap_threads[account_id] = thread
            thread.start()
        flash('Account activated', 'success')
    else:
        if account_id in imap_threads:
            del imap_threads[account_id]  # This will cause the thread to exit
        flash('Account deactivated', 'success')
    
    return redirect(url_for('email_accounts'))

@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    """Delete email account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Stop monitoring thread if running
    if account_id in imap_threads:
        del imap_threads[account_id]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()
    
    flash('Account deleted successfully', 'success')
    return redirect(url_for('email_accounts'))

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
        'total_emails': stats['total'],
        'pending_emails': stats['pending'],
        'approved_emails': stats['approved'],
        'rejected_emails': stats['rejected'],
        'high_risk_emails': stats['high_risk'],
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

@app.route('/api/diagnostics/<account_id>')
@login_required
def api_diagnostics(account_id):
    """API endpoint for per-account diagnostics"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get specific account
    account = cursor.execute("""
        SELECT * FROM email_accounts WHERE id = ?
    """, (account_id,)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    results = {
        'account_id': account_id,
        'account_name': account['account_name'],
        'smtp_test': {'success': False, 'message': ''},
        'imap_test': {'success': False, 'message': ''},
        'pop3_test': {'success': False, 'message': ''},
        'timestamp': datetime.now().isoformat()
    }
    
    # Decrypt passwords
    smtp_password = decrypt_credential(account['smtp_password'])
    imap_password = decrypt_credential(account['imap_password'])
    
    # Test SMTP connection
    try:
        import smtplib
        smtp_port = int(account['smtp_port']) if account['smtp_port'] else 587
        
        if smtp_port == 465:
            smtp = smtplib.SMTP_SSL(account['smtp_host'], smtp_port, timeout=10)
        else:
            smtp = smtplib.SMTP(account['smtp_host'], smtp_port, timeout=10)
            smtp.starttls()
        
        smtp.login(account['smtp_username'], smtp_password)
        smtp.quit()
        results['smtp_test']['success'] = True
        results['smtp_test']['message'] = f"Connected successfully to {account['smtp_host']}:{smtp_port}"
    except Exception as e:
        results['smtp_test']['message'] = str(e)
    
    # Test IMAP connection
    try:
        import imaplib
        imap_port = int(account['imap_port']) if account['imap_port'] else 993
        
        imap = imaplib.IMAP4_SSL(account['imap_host'], imap_port)
        imap.login(account['imap_username'], imap_password)
        imap.select('INBOX')
        imap.close()
        imap.logout()
        results['imap_test']['success'] = True
        results['imap_test']['message'] = f"Connected successfully to {account['imap_host']}:{imap_port}"
    except Exception as e:
        results['imap_test']['message'] = str(e)
    
    # Test POP3 if configured
    if account['pop3_host']:
        try:
            import poplib
            pop3_password = decrypt_credential(account['pop3_password'])
            if account['pop3_use_ssl']:
                pop3 = poplib.POP3_SSL(account['pop3_host'], account['pop3_port'])
            else:
                pop3 = poplib.POP3(account['pop3_host'], account['pop3_port'])
            pop3.user(account['pop3_username'])
            pop3.pass_(pop3_password)
            pop3.quit()
            results['pop3_test']['success'] = True
            results['pop3_test']['message'] = f"Connected successfully to {account['pop3_host']}:{account['pop3_port']}"
        except Exception as e:
            results['pop3_test']['message'] = str(e)
    
    # Update health status in database
    cursor.execute("""
        UPDATE email_accounts 
        SET smtp_health_status = ?, imap_health_status = ?, pop3_health_status = ?, 
            last_health_check = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        'connected' if results['smtp_test']['success'] else 'error',
        'connected' if results['imap_test']['success'] else 'error',
        'connected' if results.get('pop3_test', {}).get('success') else 'unknown',
        account_id
    ))
    conn.commit()
    conn.close()
    
    return jsonify(results)

@app.route('/api/accounts/<account_id>/health')
@login_required
def api_account_health(account_id):
    """Get real-time health status for an account"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    account = cursor.execute("""
        SELECT smtp_health_status, imap_health_status, pop3_health_status,
               last_health_check, last_error, connection_status
        FROM email_accounts WHERE id = ?
    """, (account_id,)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Determine overall status
    smtp_status = account['smtp_health_status'] or 'unknown'
    imap_status = account['imap_health_status'] or 'unknown'
    pop3_status = account['pop3_health_status'] or 'unknown'
    
    if smtp_status == 'connected' and imap_status == 'connected':
        overall = 'connected'
    elif smtp_status == 'error' or imap_status == 'error':
        overall = 'error'
    elif smtp_status == 'unknown' and imap_status == 'unknown':
        overall = 'unknown'
    else:
        overall = 'warning'
    
    conn.close()
    
    return jsonify({
        'overall': overall,
        'smtp': smtp_status,
        'imap': imap_status,
        'pop3': pop3_status,
        'last_check': account['last_health_check'],
        'last_error': account['last_error']
    })

@app.route('/api/accounts/<account_id>/test', methods=['POST'])
@login_required
def api_test_account(account_id):
    """Test account connections and update health status"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    account = cursor.execute("SELECT * FROM email_accounts WHERE id = ?", (account_id,)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Decrypt passwords
    imap_password = decrypt_credential(account['imap_password'])
    smtp_password = decrypt_credential(account['smtp_password'])
    
    # Test connections
    imap_success, imap_msg = test_email_connection('imap', account['imap_host'], 
                                                   account['imap_port'], account['imap_username'], 
                                                   imap_password, account['imap_use_ssl'])
    
    smtp_success, smtp_msg = test_email_connection('smtp', account['smtp_host'], 
                                                   account['smtp_port'], account['smtp_username'], 
                                                   smtp_password, account['smtp_use_ssl'])
    
    # Update health status
    cursor.execute("""
        UPDATE email_accounts 
        SET smtp_health_status = ?, imap_health_status = ?, 
            last_health_check = CURRENT_TIMESTAMP,
            connection_status = ?
        WHERE id = ?
    """, (
        'connected' if smtp_success else 'error',
        'connected' if imap_success else 'error',
        'connected' if (smtp_success and imap_success) else 'error',
        account_id
    ))
    
    if smtp_success and imap_success:
        cursor.execute("""
            UPDATE email_accounts 
            SET last_successful_connection = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (account_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': smtp_success and imap_success,
        'imap': {'success': imap_success, 'message': imap_msg},
        'smtp': {'success': smtp_success, 'message': smtp_msg}
    })

@app.route('/api/accounts/<account_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_account_crud(account_id):
    """Handle account CRUD operations"""
    if request.method == 'GET':
        # Get account details
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        account = cursor.execute("SELECT * FROM email_accounts WHERE id = ?", (account_id,)).fetchone()
        
        if not account:
            conn.close()
            return jsonify({'error': 'Account not found'}), 404
        
        # Don't send encrypted passwords
        account_data = dict(account)
        account_data.pop('imap_password', None)
        account_data.pop('smtp_password', None)
        account_data.pop('pop3_password', None)
        
        conn.close()
        return jsonify(account_data)
    
    elif request.method == 'PUT':
        # Update account
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build update query
        update_fields = []
        update_values = []
        
        for field in ['account_name', 'email_address', 'provider_type', 
                     'smtp_host', 'smtp_port', 'smtp_username',
                     'imap_host', 'imap_port', 'imap_username']:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        # Handle passwords
        if 'smtp_password' in data and data['smtp_password']:
            update_fields.append("smtp_password = ?")
            update_values.append(encrypt_credential(data['smtp_password']))
        
        if 'imap_password' in data and data['imap_password']:
            update_fields.append("imap_password = ?")
            update_values.append(encrypt_credential(data['imap_password']))
        
        # Handle SSL flags
        if 'smtp_use_ssl' in data:
            update_fields.append("smtp_use_ssl = ?")
            update_values.append(1 if data['smtp_use_ssl'] else 0)
        
        if 'imap_use_ssl' in data:
            update_fields.append("imap_use_ssl = ?")
            update_values.append(1 if data['imap_use_ssl'] else 0)
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(account_id)
            query = f"UPDATE email_accounts SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, update_values)
            conn.commit()
        
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        # Delete account
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        # Stop monitoring thread
        if int(account_id) in imap_threads:
            del imap_threads[int(account_id)]
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM email_accounts WHERE id = ?", (account_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})

@app.route('/api/accounts/export')
@login_required
def api_export_accounts():
    """Export accounts configuration"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    accounts = cursor.execute("""
        SELECT account_name, email_address, provider_type,
               imap_host, imap_port, imap_username, imap_use_ssl,
               smtp_host, smtp_port, smtp_username, smtp_use_ssl
        FROM email_accounts
        ORDER BY account_name
    """).fetchall()
    
    conn.close()
    
    export_data = {
        'version': '1.0',
        'exported_at': datetime.now().isoformat(),
        'accounts': [dict(account) for account in accounts]
    }
    
    response = jsonify(export_data)
    response.headers['Content-Disposition'] = 'attachment; filename=email_accounts_export.json'
    return response

@app.route('/api/accounts/<int:account_id>')
@login_required
def api_get_account(account_id):
    """Get account details for testing"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    account = cursor.execute("""
        SELECT * FROM email_accounts WHERE id = ?
    """, (account_id,)).fetchone()
    
    conn.close()
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Decrypt password for testing
    key = get_encryption_key()
    fernet = Fernet(key)
    
    account_data = dict(account)
    try:
        account_data['imap_password'] = fernet.decrypt(account['imap_password'].encode()).decode()
        account_data['smtp_password'] = fernet.decrypt(account['smtp_password'].encode()).decode()
    except:
        # Passwords might not be encrypted
        pass
    
    return jsonify(account_data)

@app.route('/api/test-connection/<connection_type>', methods=['POST'])
@login_required
def api_test_connection(connection_type):
    """Test email connection (IMAP or SMTP)"""
    data = request.json or request.get_json(force=True)
    
    host = data.get('host')
    port = int(data.get('port'))
    username = data.get('username')
    password = data.get('password')
    use_ssl = data.get('use_ssl', True)
    
    success, message = test_email_connection(connection_type, host, port, username, password, use_ssl)
    
    return jsonify({
        'success': success,
        'message': message,
        'error': message if not success else None
    })

@app.route('/diagnostics')
@app.route('/diagnostics/<account_id>')
@login_required
def diagnostics(account_id=None):
    """Email connectivity diagnostics page (per-account)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all accounts
    accounts = cursor.execute("""
        SELECT id, account_name, email_address, imap_host, imap_port, smtp_host, smtp_port,
               is_active, last_checked, last_error, smtp_username, smtp_password
        FROM email_accounts
        ORDER BY account_name
    """).fetchall()
    
    results = {}
    selected_account = None
    
    if account_id:
        # Get specific account
        selected_account = cursor.execute("""
            SELECT * FROM email_accounts WHERE id = ?
        """, (account_id,)).fetchone()
        
        if selected_account:
            # Run diagnostics for this specific account
            try:
                import smtplib
                import imaplib
                from datetime import datetime
                
                results = {
                    'account': dict(selected_account),
                    'smtp_test': {'success': False, 'message': ''},
                    'imap_test': {'success': False, 'message': ''},
                    'timestamp': datetime.now().isoformat()
                }
                
                # Test SMTP connection
                try:
                    # Decrypt SMTP password
                    smtp_password = decrypt_credential(selected_account['smtp_password'])
                    smtp_port = int(selected_account['smtp_port']) if selected_account['smtp_port'] else 587
                    
                    if smtp_port == 465:
                        smtp = smtplib.SMTP_SSL(selected_account['smtp_host'], smtp_port)
                    else:
                        smtp = smtplib.SMTP(selected_account['smtp_host'], smtp_port)
                        smtp.starttls()
                    
                    smtp.login(selected_account['smtp_username'], smtp_password)
                    smtp.quit()
                    results['smtp_test']['success'] = True
                    results['smtp_test']['message'] = f"SMTP connection successful to {selected_account['smtp_host']}"
                except Exception as e:
                    results['smtp_test']['message'] = f"SMTP Error: {str(e)}"
                
                # Test IMAP connection
                try:
                    # Decrypt IMAP credentials (not SMTP)
                    imap_password = decrypt_credential(selected_account['imap_password'])
                    imap_port = int(selected_account['imap_port']) if selected_account['imap_port'] else 993
                    
                    imap = imaplib.IMAP4_SSL(selected_account['imap_host'], imap_port)
                    imap.login(selected_account['imap_username'], imap_password)
                    imap.select('INBOX')
                    imap.close()
                    imap.logout()
                    results['imap_test']['success'] = True
                    results['imap_test']['message'] = f"IMAP connection successful to {selected_account['imap_host']}"
                except Exception as e:
                    results['imap_test']['message'] = f"IMAP Error: {str(e)}"
                    
            except Exception as e:
                results = {'error': str(e)}
    
    conn.close()
    
    # Redirect to dashboard with diagnostics tab
    if account_id:
        return redirect(url_for('dashboard', tab='diagnostics') + f'?account_id={account_id}')
    else:
        return redirect(url_for('dashboard', tab='diagnostics'))

@app.route('/diagnostics/test', methods=['POST'])
@login_required
def test_email_send():
    """Test sending an email"""
    from email_diagnostics import EmailDiagnostics
    
    to_address = request.form.get('to_address', '')
    if not to_address:
        to_address = None
    
    diagnostics = EmailDiagnostics()
    result = diagnostics.test_send_email(to_address)
    
    if result['sent']:
        flash(f"Test email sent successfully to {result['to']}", 'success')
    else:
        flash(f"Failed to send test email: {result.get('error', 'Unknown error')}", 'error')
    
    return redirect(url_for('diagnostics'))

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
    
    # Keep the thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()

# Initialize database
init_database()

if __name__ == '__main__':
    # Start SMTP proxy in background thread
    smtp_thread = threading.Thread(target=run_smtp_proxy, daemon=True)
    smtp_thread.start()
    
    # Start monitoring threads for existing active accounts
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    active_accounts = cursor.execute("""
        SELECT id, account_name FROM email_accounts WHERE is_active = 1
    """).fetchall()
    conn.close()
    
    for account in active_accounts:
        account_id = account['id']
        thread = threading.Thread(target=monitor_imap_account, args=(account_id,), daemon=True)
        imap_threads[account_id] = thread
        thread.start()
        print(f"   📬 Started monitoring for {account['account_name']} (ID: {account_id})")
    
    # Give services time to start
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
    print("   • IMAP/SMTP email interception")
    print("   • Multi-account monitoring")
    print("   • Real-time email moderation")
    print("   • Risk scoring system")
    print("   • Complete audit trail")
    print("   • Encrypted credential storage")
    print("   • Modern responsive UI")
    print("\n" + "="*60 + "\n")
    
    # Run Flask app
    app.run(debug=True, use_reloader=False)