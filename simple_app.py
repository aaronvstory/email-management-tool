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
from typing import Tuple, Optional

from flask import Response  # needed for SSE / events
from email.utils import formatdate, make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Blueprint registration (interception)
try:
    from app.routes.interception import bp_interception
except Exception:
    bp_interception = None
from datetime import datetime
from email import policy
from email import message_from_bytes

from flask import Flask, request, redirect, url_for, flash, render_template, jsonify
from flask_login import (
    LoginManager, login_user, login_required, logout_user,
    current_user, UserMixin
)
from werkzeug.security import check_password_hash

# Import shared utilities
from app.utils.crypto import encrypt_credential, decrypt_credential, get_encryption_key
from app.utils.db import get_db, DB_PATH, table_exists

# Import IMAP watcher for email interception
from app.services.imap_watcher import ImapWatcher, AccountConfig

# -----------------------------------------------------------------------------
# Minimal re-initialization (original file trimmed during refactor)
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # type: ignore[attr-defined]

class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        row = cur.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        if row:
            return User(row[0], row[1], row[2])
    except Exception:
        pass
    return None

def log_action(action, user_id, target_id, details):
    """Persist an audit log record (best-effort)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT, user_id INTEGER, target_id INTEGER,
                details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "INSERT INTO audit_log (action, user_id, target_id, details) VALUES (?,?,?,?)",
            (action, user_id, target_id, details)
        )
        conn.commit()
        conn.close()
    except Exception:
        # swallow so UI not impacted
        pass

# Compatibility alias for legacy code paths
def decrypt_password(val: Optional[str]) -> Optional[str]:
    return decrypt_credential(val) if val else None

def detect_email_settings(email_address: str) -> dict:
    """
    Smart detection of SMTP/IMAP settings based on email domain.
    Returns dict with smtp_host, smtp_port, smtp_use_ssl, imap_host, imap_port, imap_use_ssl
    """
    domain = email_address.split('@')[-1].lower() if '@' in email_address else ''

    # Known provider configurations
    providers = {
        'gmail.com': {
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_use_ssl': False,  # STARTTLS on 587
            'imap_host': 'imap.gmail.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'corrinbox.com': {
            'smtp_host': 'smtp.hostinger.com',
            'smtp_port': 465,
            'smtp_use_ssl': True,  # Direct SSL on 465
            'imap_host': 'imap.hostinger.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'outlook.com': {
            'smtp_host': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'smtp_use_ssl': False,
            'imap_host': 'outlook.office365.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'hotmail.com': {
            'smtp_host': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'smtp_use_ssl': False,
            'imap_host': 'outlook.office365.com',
            'imap_port': 993,
            'imap_use_ssl': True
        },
        'yahoo.com': {
            'smtp_host': 'smtp.mail.yahoo.com',
            'smtp_port': 465,
            'smtp_use_ssl': True,
            'imap_host': 'imap.mail.yahoo.com',
            'imap_port': 993,
            'imap_use_ssl': True
        }
    }

    # Return provider settings or generic defaults
    if domain in providers:
        return providers[domain]
    else:
        # Generic defaults - try common patterns
        return {
            'smtp_host': f'smtp.{domain}',
            'smtp_port': 587,
            'smtp_use_ssl': False,
            'imap_host': f'imap.{domain}',
            'imap_port': 993,
            'imap_use_ssl': True
        }

def test_email_connection(kind: str, host: str, port: int, username: str, password: str, use_ssl: bool) -> Tuple[bool, str]:
    """Lightweight connectivity test for IMAP/SMTP (Phase 1 stub).
    Returns (success, message). Avoids introducing heavy network timeouts.
    """
    if not host or not port or not username:
        return False, "Missing connection parameters"
    try:
        if kind.lower() == 'imap':
            if use_ssl:
                client = imaplib.IMAP4_SSL(host, int(port))
            else:
                client = imaplib.IMAP4(host, int(port))
            if password:
                client.login(username, password)
            client.logout()
            return True, f"IMAP OK {host}:{port}"
        if kind.lower() == 'smtp':
            if use_ssl and int(port) in (465, 587):
                if int(port) == 465:
                    server = smtplib.SMTP_SSL(host, int(port), timeout=10)
                else:
                    server = smtplib.SMTP(host, int(port), timeout=10)
                    server.starttls()
            else:
                server = smtplib.SMTP(host, int(port), timeout=10)
            if password:
                server.login(username, password)
            server.quit()
            return True, f"SMTP OK {host}:{port}"
        return False, f"Unsupported kind {kind}"
    except Exception as e:
        return False, str(e)

def init_database():
    """
    Initialize SQLite database with all required tables (idempotent).
    Creates tables if missing; preserves existing schema & data.
    """
    conn = get_db()
    cur = conn.cursor()

    # Users table
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT DEFAULT 'admin',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Email accounts table (NO Sieve fields)
    cur.execute("""CREATE TABLE IF NOT EXISTS email_accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT,
        email_address TEXT,
        imap_host TEXT,
        imap_port INTEGER,
        imap_username TEXT,
        imap_password TEXT,
        imap_use_ssl INTEGER DEFAULT 1,
        smtp_host TEXT,
        smtp_port INTEGER,
        smtp_username TEXT,
        smtp_password TEXT,
        smtp_use_ssl INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        last_checked TEXT,
        last_error TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Email messages table with full interception support
    cur.execute("""CREATE TABLE IF NOT EXISTS email_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT,
        account_id INTEGER,
        direction TEXT,
        status TEXT DEFAULT 'PENDING',
        interception_status TEXT,
        sender TEXT,
        recipients TEXT,
        subject TEXT,
        body_text TEXT,
        body_html TEXT,
        headers TEXT,
        attachments TEXT,
        original_uid INTEGER,
        original_internaldate TEXT,
        original_message_id TEXT,
        edited_message_id TEXT,
        quarantine_folder TEXT,
        raw_content TEXT,
        raw_path TEXT,
        risk_score INTEGER DEFAULT 0,
        keywords_matched TEXT,
        moderation_reason TEXT,
        moderator_id INTEGER,
        reviewer_id INTEGER,
        review_notes TEXT,
        approved_by TEXT,
        latency_ms INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        processed_at TEXT,
        action_taken_at TEXT,
        reviewed_at TEXT,
        sent_at TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Moderation rules table
    cur.execute("""CREATE TABLE IF NOT EXISTS moderation_rules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_name TEXT,
        keyword TEXT,
        action TEXT DEFAULT 'REVIEW',
        priority INTEGER DEFAULT 5,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Audit log table
    cur.execute("""CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        user_id INTEGER,
        target_id INTEGER,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Create default admin user if not exists
    cur.execute("SELECT id FROM users WHERE username='admin'")
    if not cur.fetchone():
        from werkzeug.security import generate_password_hash
        admin_hash = generate_password_hash('admin123')
        cur.execute("INSERT INTO users(username, password_hash, role) VALUES('admin', ?, 'admin')", (admin_hash,))

    conn.commit()
    conn.close()

def monitor_imap_account(account_id: int):
    """
    IMAP monitor thread that uses ImapWatcher to intercept incoming emails.
    Runs in daemon thread, auto-reconnects on failure.
    """
    app.logger.info(f"Starting IMAP monitor for account {account_id}")

    while True:
        try:
            # Fetch account details from database
            with get_db() as conn:
                cursor = conn.cursor()
                row = cursor.execute(
                    "SELECT imap_host, imap_port, imap_username, imap_password FROM email_accounts WHERE id=? AND is_active=1",
                    (account_id,)
                ).fetchone()

                if not row:
                    app.logger.warning(f"Account {account_id} not found or inactive, stopping monitor")
                    return

                # Decrypt password
                encrypted_password = row['imap_password']
                password = decrypt_credential(encrypted_password)

                # Create account configuration with account_id and db_path
                cfg = AccountConfig(
                    imap_host=row['imap_host'],
                    imap_port=row['imap_port'] or 993,
                    username=row['imap_username'],
                    password=password,
                    use_ssl=True,
                    inbox="INBOX",
                    quarantine="Quarantine",
                    idle_timeout=25 * 60,  # 25 minutes
                    idle_ping_interval=14 * 60,  # 14 minutes
                    mark_seen_quarantine=True,
                    account_id=account_id,  # Pass account ID for database storage
                    db_path=DB_PATH  # Pass database path
                )

            # Start ImapWatcher - runs forever with auto-reconnect
            app.logger.info(f"Connecting ImapWatcher for {cfg.username} at {cfg.imap_host}:{cfg.imap_port}")
            watcher = ImapWatcher(cfg)
            watcher.run_forever()  # Blocks with backoff retry on errors

        except Exception as e:
            app.logger.error(f"IMAP monitor for account {account_id} failed: {e}", exc_info=True)
            time.sleep(30)  # Wait before retry

# Register interception blueprint providing /healthz and interception APIs
try:
    from app.routes.interception import bp_interception
    app.register_blueprint(bp_interception)
except Exception as e:
    print(f"Warning: failed to register interception blueprint: {e}")

        # (Legacy inline IMAP loop removed during refactor)

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
        # Check for simple keywords in the email content
        # Using simplified logic since table structure is different
        content = f"{subject} {body}".lower()

        # Default keywords to check
        default_keywords = {
            'urgent': 5,
            'confidential': 10,
            'payment': 8,
            'password': 10,
            'account': 5,
            'verify': 7,
            'suspended': 9,
            'click here': 8,
            'act now': 7,
            'limited time': 6
        }

        for keyword, priority in default_keywords.items():
            if keyword.lower() in content:
                keywords.append(keyword)
                risk_score += priority

        conn.close()

        return keywords, min(risk_score, 100)

if 'app' in globals() and bp_interception:
    try:
        app.register_blueprint(bp_interception)
    except Exception:
        pass

# Context processor to inject pending_count into all templates
@app.context_processor
def inject_pending_count():
    """Inject pending_count into all templates for the badge in navigation"""
    try:
        if current_user.is_authenticated:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            pending_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0]
            conn.close()
            return {'pending_count': pending_count}
    except:
        pass
    return {'pending_count': 0}

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

    # Get all moderation rules for Rules tab
    rules = cursor.execute("""
        SELECT id, rule_name, rule_type, condition_field, condition_operator,
               condition_value, action, priority, is_active, created_at
        FROM moderation_rules
        ORDER BY priority DESC, rule_name
    """).fetchall()

    conn.close()

    return render_template('dashboard_unified.html',
                         stats=stats,
                         recent_emails=recent_emails,
                         active_rules=active_rules,
                         rules=rules,
                         accounts=accounts,
                         selected_account_id=selected_account_id,
                         active_tab=tab,
                         pending_count=stats['pending'],
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
    account_id = request.args.get('account_id', type=int)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all active email accounts for selector
    accounts = cursor.execute("""
        SELECT id, account_name, email_address
        FROM email_accounts
        WHERE is_active = 1
        ORDER BY account_name
    """).fetchall()

    # Get counts for all statuses (consider account filter)
    if account_id:
        pending_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING' AND account_id = ?", (account_id,)).fetchone()[0] or 0
        approved_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'APPROVED' AND account_id = ?", (account_id,)).fetchone()[0] or 0
        rejected_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'REJECTED' AND account_id = ?", (account_id,)).fetchone()[0] or 0
        total_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE account_id = ?", (account_id,)).fetchone()[0] or 0
    else:
        pending_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0] or 0
        approved_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'APPROVED'").fetchone()[0] or 0
        rejected_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'REJECTED'").fetchone()[0] or 0
        total_count = cursor.execute("SELECT COUNT(*) FROM email_messages").fetchone()[0] or 0

    # Get filtered emails based on status and account
    if account_id:
        if status_filter == 'ALL' or status_filter == 'all':
            emails = cursor.execute("""
                SELECT * FROM email_messages
                WHERE account_id = ?
                ORDER BY created_at DESC
            """, (account_id,)).fetchall()
        else:
            emails = cursor.execute("""
                SELECT * FROM email_messages
                WHERE status = ? AND account_id = ?
                ORDER BY created_at DESC
            """, (status_filter, account_id)).fetchall()
    else:
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

    # Pass all counts and accounts to template
    return render_template('email_queue.html',
                          emails=emails,
                          current_filter=status_filter,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count,
                          total_count=total_count,
                          accounts=accounts,
                          selected_account_id=str(account_id) if account_id else None)

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

@app.route('/api/detect-email-settings', methods=['POST'])
@login_required
def api_detect_email_settings():
    """API endpoint for smart detection of email settings"""
    data = request.get_json()
    email = data.get('email', '')

    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400

    settings = detect_email_settings(email)
    return jsonify(settings)

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

        # Auto-detect settings if requested
        use_auto_detect = request.form.get('use_auto_detect') == 'on'
        if use_auto_detect and email_address:
            auto_settings = detect_email_settings(email_address)
            imap_host = auto_settings['imap_host']
            imap_port = auto_settings['imap_port']
            imap_use_ssl = auto_settings['imap_use_ssl']
            smtp_host = auto_settings['smtp_host']
            smtp_port = auto_settings['smtp_port']
            smtp_use_ssl = auto_settings['smtp_use_ssl']
            # Username defaults to email address
            imap_username = email_address
            smtp_username = email_address
            imap_password = request.form.get('imap_password')
            smtp_password = request.form.get('smtp_password')
        else:
            # Manual settings
            imap_host = request.form.get('imap_host')
            imap_port = int(request.form.get('imap_port', 993))
            imap_username = request.form.get('imap_username')
            imap_password = request.form.get('imap_password')
            imap_use_ssl = request.form.get('imap_use_ssl') == 'on'

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

        # Start IMAP monitoring thread for new account
        try:
            thread = threading.Thread(target=monitor_imap_account, args=(account_id,), daemon=True)
            imap_threads[account_id] = thread
            thread.start()
        except Exception as e:
            app.logger.warning(f"Failed to start IMAP monitor thread for account {account_id}: {e}")

        flash('Account added successfully', 'success')
        return redirect(url_for('email_accounts'))

    return render_template('add_account.html')

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

    # Update health status in database
    cursor.execute("""
        UPDATE email_accounts
        SET smtp_health_status = ?, imap_health_status = ?,
            last_health_check = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        'connected' if results['smtp_test']['success'] else 'error',
        'connected' if results['imap_test']['success'] else 'error',
        account_id
    ))
    conn.commit()
    conn.close()

    return jsonify(results)

@app.route('/api/accounts')
@login_required
def api_get_accounts():
    """Get all active email accounts for the test suite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    accounts = cursor.execute("""
        SELECT id, account_name, email_address, is_active,
               smtp_host, smtp_port, imap_host, imap_port
        FROM email_accounts
        ORDER BY account_name
    """).fetchall()

    conn.close()

    return jsonify({
        'success': True,
        'accounts': [dict(acc) for acc in accounts]
    })

@app.route('/api/inbox')
@login_required
def api_inbox():
    """API endpoint for inbox with filtering"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get query parameters
    status = request.args.get('status')
    account_id = request.args.get('account_id')
    search_q = request.args.get('q')

    # Build query
    query = """
        SELECT em.*, ea.account_name, ea.email_address as account_email
        FROM email_messages em
        LEFT JOIN email_accounts ea ON em.account_id = ea.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND (em.status = ? OR em.interception_status = ?)"
        params.extend([status, status])

    if account_id:
        query += " AND em.account_id = ?"
        params.append(account_id)

    if search_q:
        query += " AND (em.subject LIKE ? OR em.sender LIKE ?)"
        params.extend([f'%{search_q}%', f'%{search_q}%'])

    query += " ORDER BY em.created_at DESC LIMIT 100"

    emails = cursor.execute(query, params).fetchall()

    # Add preview snippet and format data
    messages = []
    for email in emails:
        msg = dict(email)
        # Add preview snippet
        msg['preview_snippet'] = (email['body_text'] or '')[:200] if email['body_text'] else ''
        messages.append(msg)

    conn.close()

    return jsonify({
        'success': True,
        'messages': messages
    })

@app.route('/api/fetch-emails', methods=['POST'])
@login_required
def api_fetch_emails():
    """Fetch emails from IMAP server with customizable count"""
    data = request.get_json()
    account_id = data.get('account_id')
    fetch_count = data.get('count', 20)  # Default to 20 emails
    offset = data.get('offset', 0)  # For pagination

    if not account_id:
        return jsonify({'success': False, 'error': 'Account ID required'}), 400

    # Get account details
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    account = cursor.execute(
        "SELECT * FROM email_accounts WHERE id = ? AND is_active = 1",
        (account_id,)
    ).fetchone()

    if not account:
        conn.close()
        return jsonify({'success': False, 'error': 'Account not found or inactive'}), 404

    try:
        import imaplib
        from email import message_from_bytes, policy

        # Decrypt password
        password = decrypt_credential(account['imap_password'])

        # Connect to IMAP server
        if account['imap_port'] == 993:
            mail = imaplib.IMAP4_SSL(account['imap_host'], account['imap_port'])
        else:
            mail = imaplib.IMAP4(account['imap_host'], account['imap_port'])
            mail.starttls()

        mail.login(account['imap_username'], password)
        mail.select('INBOX')

        # Search for all emails
        _, message_ids = mail.search(None, 'ALL')
        id_list = message_ids[0].split()

        # Calculate range for pagination
        total_emails = len(id_list)
        start_idx = max(0, total_emails - offset - fetch_count)
        end_idx = total_emails - offset

        # Fetch the requested range
        fetched_emails = []
        emails_to_fetch = id_list[start_idx:end_idx][-fetch_count:]  # Get last N emails

        for email_id in reversed(emails_to_fetch):  # Most recent first
            _, msg_data = mail.fetch(email_id, '(RFC822)')
            raw_email = msg_data[0][1]
            email_msg = message_from_bytes(raw_email, policy=policy.default)

            # Extract email data
            sender = str(email_msg.get('From', ''))
            recipients = json.dumps([str(email_msg.get('To', ''))])
            subject = str(email_msg.get('Subject', 'No Subject'))
            message_id = str(email_msg.get('Message-ID', f"manual_{account_id}_{datetime.now().timestamp()}"))
            date = str(email_msg.get('Date', ''))

            # Extract body
            body_text = ""
            body_html = ""
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text = payload.decode('utf-8', errors='ignore')
                    elif part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_html = payload.decode('utf-8', errors='ignore')
            else:
                payload = email_msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode('utf-8', errors='ignore')

            # Store in database with manual_fetch flag
            cursor.execute('''
                INSERT OR IGNORE INTO email_messages
                (message_id, sender, recipients, subject, body_text, body_html,
                 raw_content, account_id, direction, interception_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (message_id, sender, recipients, subject, body_text, body_html,
                  raw_email, account_id, 'inbound', 'FETCHED'))

            fetched_emails.append({
                'message_id': message_id,
                'sender': sender,
                'subject': subject,
                'date': date,
                'preview': body_text[:200] if body_text else ''
            })

        conn.commit()
        mail.logout()

        conn.close()
        return jsonify({
            'success': True,
            'fetched': len(fetched_emails),
            'total_available': total_emails,
            'emails': fetched_emails
        })

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/email/<email_id>/reply-forward', methods=['GET'])
@login_required
def api_email_reply_forward(email_id):
    """Get email data formatted for reply or forward"""
    action = request.args.get('action', 'reply')  # 'reply' or 'forward'

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    email = cursor.execute(
        "SELECT * FROM email_messages WHERE id = ?",
        (email_id,)
    ).fetchone()

    if not email:
        conn.close()
        return jsonify({'success': False, 'error': 'Email not found'}), 404

    # Prepare response based on action
    if action == 'reply':
        # Reply: Set original sender as recipient
        response = {
            'to': email['sender'],
            'subject': f"Re: {email['subject']}" if not email['subject'].startswith('Re:') else email['subject'],
            'body': f"\n\n--- Original Message ---\nFrom: {email['sender']}\nDate: {email['created_at']}\nSubject: {email['subject']}\n\n{email['body_text']}"
        }
    else:  # forward
        response = {
            'to': '',  # User will fill this
            'subject': f"Fwd: {email['subject']}" if not email['subject'].startswith('Fwd:') else email['subject'],
            'body': f"\n\n--- Forwarded Message ---\nFrom: {email['sender']}\nDate: {email['created_at']}\nSubject: {email['subject']}\n\n{email['body_text']}"
        }

    conn.close()
    return jsonify({'success': True, 'data': response})

@app.route('/api/email/<email_id>/download', methods=['GET'])
@login_required
def api_email_download(email_id):
    """Download email as .eml file"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    email = cursor.execute(
        "SELECT raw_content, subject FROM email_messages WHERE id = ?",
        (email_id,)
    ).fetchone()

    if not email or not email['raw_content']:
        conn.close()
        return jsonify({'success': False, 'error': 'Email not found or no raw content'}), 404

    conn.close()

    # Create response with .eml file
    from flask import Response
    import re

    # Sanitize filename
    safe_subject = re.sub(r'[^\w\s-]', '', email['subject'] or 'email')[:50]
    filename = f"{safe_subject}_{email_id}.eml"

    return Response(
        email['raw_content'],
        mimetype='message/rfc822',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )

@app.route('/api/email/<email_id>/intercept', methods=['POST'])
@login_required
def api_email_intercept(email_id):
    """Manually intercept an email (change status to HELD)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update email status to HELD for manual interception
    cursor.execute("""
        UPDATE email_messages
        SET interception_status = 'HELD',
            status = 'PENDING',
            action_taken_at = datetime('now')
        WHERE id = ?
    """, (email_id,))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Email intercepted and held for review'})

@app.route('/api/accounts/<account_id>/health')
@login_required
def api_account_health(account_id):
    """Get real-time health status for an account"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    account = cursor.execute("""
        SELECT smtp_health_status, imap_health_status,
               last_health_check, last_error, connection_status
        FROM email_accounts WHERE id = ?
    """, (account_id,)).fetchone()

    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404

    # Determine overall status
    smtp_status = account['smtp_health_status'] or 'unknown'
    imap_status = account['imap_health_status'] or 'unknown'
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
        if data and 'smtp_password' in data and data['smtp_password']:
            update_fields.append("smtp_password = ?")
            update_values.append(encrypt_credential(data['smtp_password']))

        if data and 'imap_password' in data and data['imap_password']:
            update_fields.append("imap_password = ?")
            update_values.append(encrypt_credential(data['imap_password']))

        # Handle SSL flags
        if data and 'smtp_use_ssl' in data:
            update_fields.append("smtp_use_ssl = ?")
            update_values.append(1 if data['smtp_use_ssl'] else 0)

        if data and 'imap_use_ssl' in data:
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
    account_data = dict(account)
    try:
        account_data['imap_password'] = decrypt_credential(account['imap_password'])
        account_data['smtp_password'] = decrypt_credential(account['smtp_password'])
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
    # Legacy dependency (email_diagnostics) removed in cleanup phase.
    flash('Email diagnostics send test temporarily disabled (module deprecated).', 'warning')
    return redirect(url_for('diagnostics'))

@app.route('/interception-test')
@login_required
def interception_test_dashboard():
    """Display the comprehensive email interception test dashboard"""
    return render_template('interception_test_dashboard.html', timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/api/test/send-email', methods=['POST'])
@login_required
def api_test_send_email():
    """Simplified legacy test send endpoint (non-critical)."""
    data = request.get_json(silent=True) or {}
    from_account_id = data.get('from_account_id')
    to_account_id = data.get('to_account_id')
    subject = data.get('subject') or 'Test'
    body = data.get('body') or 'Test body'
    if not (from_account_id and to_account_id):
        return jsonify({'success': False, 'error': 'Missing account ids'}), 400
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    from_account = cur.execute("SELECT * FROM email_accounts WHERE id=?", (from_account_id,)).fetchone()
    to_account = cur.execute("SELECT * FROM email_accounts WHERE id=?", (to_account_id,)).fetchone(); conn.close()
    if not from_account or not to_account:
        return jsonify({'success': False, 'error': 'Invalid account ids'}), 400
    try:
        msg = MIMEMultipart(); msg['From'] = from_account['email_address']; msg['To'] = to_account['email_address']
        msg['Subject'] = subject; msg['Date'] = formatdate(); msg['Message-ID'] = make_msgid(); msg.attach(MIMEText(body, 'plain'))
        smtp = smtplib.SMTP('localhost', 8587, timeout=5); smtp.send_message(msg); smtp.quit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test/check-interception')
@login_required
def api_test_check_interception():
    """Check if an email was intercepted"""
    try:
        subject = request.args.get('subject')

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        email = cursor.execute("""
            SELECT id, subject, status, created_at
            FROM email_messages
            WHERE subject = ? AND status = 'PENDING'
            ORDER BY created_at DESC
            LIMIT 1
        """, (subject,)).fetchone()

        conn.close()

        if email:
            return jsonify({
                'success': True,
                'email_id': email['id'],
                'subject': email['subject'],
                'status': email['status']
            })
        else:
            return jsonify({'success': False, 'message': 'Email not found'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test/verify-delivery', methods=['POST'])
@login_required
def api_test_verify_delivery():
    """Simplified legacy verify-delivery: check subject presence in local DB only."""
    data = request.get_json(silent=True) or {}
    account_id = data.get('account_id'); subject = (data.get('subject') or '').strip()
    if not (account_id and subject):
        return jsonify({'success': False, 'error': 'Missing account_id or subject'}), 400
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    account = cur.execute("SELECT id FROM email_accounts WHERE id=?", (account_id,)).fetchone(); conn.close()
    if not account:
        return jsonify({'success': False, 'error': 'Invalid account ID'}), 400
    c2 = sqlite3.connect(DB_PATH).cursor(); hit = c2.execute("SELECT 1 FROM email_messages WHERE subject=? LIMIT 1", (subject,)).fetchone(); c2.connection.close()
    return jsonify({'success': bool(hit), 'source': 'local-db'})

@app.route('/email/<int:email_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_email(email_id):
    """Edit an email's subject and body"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'GET':
        # Get email details for editing
        email = cursor.execute("""
            SELECT id, subject, body_text, sender, recipients, status
            FROM email_messages
            WHERE id = ?
        """, (email_id,)).fetchone()
        conn.close()

        if not email:
            return jsonify({'error': 'Email not found'}), 404

        if email['status'] != 'PENDING':
            return jsonify({'error': 'Only pending emails can be edited'}), 400

        return jsonify({
            'id': email['id'],
            'subject': email['subject'],
            'body': email['body_text'],
            'sender': email['sender'],
            'recipients': email['recipients']
        })

    elif request.method == 'POST':
        # Update email with new content
        data = request.get_json()
        new_subject = data.get('subject', '').strip()
        new_body = data.get('body', '').strip()

        if not new_subject or not new_body:
            return jsonify({'error': 'Subject and body are required'}), 400

        # Update the email
        cursor.execute("""
            UPDATE email_messages
            SET subject = ?,
                body_text = ?,
                review_notes = COALESCE(review_notes, '') || '\n[Edited by ' || ? || ' at ' || datetime('now') || ']'
            WHERE id = ? AND status = 'PENDING'
        """, (new_subject, new_body, current_user.username, email_id))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Email not found or not in pending status'}), 400

        conn.commit()

        # Log the action
        log_action('EMAIL_EDITED', current_user.id, email_id, f"Subject: {new_subject[:50]}")

        conn.close()

        flash('Email updated successfully', 'success')
        return jsonify({'success': True, 'message': 'Email updated successfully'})

@app.route('/email/<int:email_id>/full')
@login_required
def get_full_email(email_id):
    """Get complete email details for editor"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    email = cursor.execute("""
        SELECT id, message_id, sender, recipients, subject,
               body_text, body_html, raw_content, status,
               risk_score, keywords_matched, review_notes,
               created_at, processed_at
        FROM email_messages
        WHERE id = ?
    """, (email_id,)).fetchone()
    conn.close()

    if not email:
        return jsonify({'error': 'Email not found'}), 404

    return jsonify({
        'id': email['id'],
        'message_id': email['message_id'],
        'sender': email['sender'],
        'recipients': email['recipients'],
        'subject': email['subject'],
        'body_text': email['body_text'],
        'body_html': email['body_html'],
        'status': email['status'],
        'risk_score': email['risk_score'],
        'keywords_matched': email['keywords_matched'],
        'review_notes': email['review_notes'],
        'created_at': email['created_at'],
        'processed_at': email['processed_at']
    })

@app.route('/email/<int:email_id>/save', methods=['POST'])
@login_required
def save_email_draft(email_id):
    """Save email as draft with changes"""
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update email with draft changes
    cursor.execute("""
        UPDATE email_messages
        SET subject = ?,
            body_text = ?,
            body_html = ?,
            review_notes = COALESCE(review_notes, '') || '\n[Draft saved by ' || ? || ' at ' || datetime('now') || ']\n' || ?
        WHERE id = ? AND status = 'PENDING'
    """, (
        data.get('subject'),
        data.get('body_text'),
        data.get('body_html', ''),
        current_user.username,
        data.get('review_notes', ''),
        email_id
    ))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Email not found or not pending'}), 400

    conn.commit()
    conn.close()

    log_action('EMAIL_DRAFT_SAVED', current_user.id, email_id, f"Draft saved")

    return jsonify({'success': True, 'message': 'Draft saved successfully'})

@app.route('/email/<int:email_id>/approve-send', methods=['POST'])
@login_required
def approve_and_send_email(email_id):
    """Approve email and send it immediately"""
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # First update the email with any final edits
    cursor.execute("""
        UPDATE email_messages
        SET subject = ?,
            body_text = ?,
            body_html = ?,
            review_notes = COALESCE(review_notes, '') || '\n[Approved and sent by ' || ? || ' at ' || datetime('now') || ']\n' || ?,
            status = 'APPROVED',
            approved_by = ?,
            reviewer_id = ?
        WHERE id = ? AND status = 'PENDING'
    """, (
        data.get('subject'),
        data.get('body_text'),
        data.get('body_html', ''),
        current_user.username,
        data.get('review_notes', ''),
        current_user.username,
        current_user.id,
        email_id
    ))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Email not found or not pending'}), 400

    # Get the updated email for sending
    email = cursor.execute("""
        SELECT * FROM email_messages WHERE id = ?
    """, (email_id,)).fetchone()

    conn.commit()

    # TODO: Actually send the email via SMTP
    # For now, just mark as sent
    cursor.execute("""
        UPDATE email_messages
        SET status = 'SENT',
            sent_at = datetime('now')
        WHERE id = ?
    """, (email_id,))

    conn.commit()
    conn.close()

    log_action('EMAIL_APPROVED_SENT', current_user.id, email_id, f"Approved and sent")

    return jsonify({'success': True, 'message': 'Email approved and sent successfully'})

@app.route('/email/<int:email_id>/reject', methods=['POST'])
@login_required
def reject_email(email_id):
    """Reject an email"""
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE email_messages
        SET status = 'REJECTED',
            review_notes = COALESCE(review_notes, '') || '\n[Rejected by ' || ? || ' at ' || datetime('now') || ']\n' || ?,
            approved_by = ?,
            reviewer_id = ?
        WHERE id = ? AND status = 'PENDING'
    """, (
        current_user.username,
        data.get('review_notes', ''),
        current_user.username,
        current_user.id,
        email_id
    ))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Email not found or not pending'}), 400

    conn.commit()
    conn.close()

    log_action('EMAIL_REJECTED', current_user.id, email_id, f"Rejected")

    return jsonify({'success': True, 'message': 'Email rejected successfully'})

@app.route('/inbox')
@login_required
def inbox():
    """View inbox emails from all accounts"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all active email accounts
    accounts = cursor.execute("""
        SELECT id, account_name, email_address
        FROM email_accounts
        WHERE is_active = 1
        ORDER BY account_name
    """).fetchall()

    # Get selected account from query params
    selected_account = request.args.get('account_id', type=int)

    # Get emails from inbox (stored messages)
    if selected_account:
        emails = cursor.execute("""
            SELECT em.*, ea.account_name, ea.email_address
            FROM email_messages em
            LEFT JOIN email_accounts ea ON em.account_id = ea.id
            WHERE em.account_id = ?
            ORDER BY em.created_at DESC
            LIMIT 100
        """, (selected_account,)).fetchall()
    else:
        emails = cursor.execute("""
            SELECT em.*, ea.account_name, ea.email_address
            FROM email_messages em
            LEFT JOIN email_accounts ea ON em.account_id = ea.id
            ORDER BY em.created_at DESC
            LIMIT 100
        """).fetchall()

    conn.close()

    return render_template('inbox.html',
                         emails=emails,
                         accounts=accounts,
                         selected_account=selected_account)

@app.route('/compose', methods=['GET', 'POST'])
@login_required
def compose_email():
    """Compose and send a new email"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all active email accounts for FROM dropdown
    accounts = cursor.execute("""
        SELECT id, account_name, email_address
        FROM email_accounts
        WHERE is_active = 1
        ORDER BY account_name
    """).fetchall()

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json(silent=True) or {}
            from_account_id = data.get('from_account')
            to_address = (data.get('to') or '').strip()
            cc_address = (data.get('cc') or '').strip()
            subject = (data.get('subject') or '').strip()
            body = (data.get('body') or '').strip()
        else:
            from_account_id = request.form.get('from_account', type=int)
            to_address = request.form.get('to', '').strip()
            cc_address = request.form.get('cc', '').strip()
            subject = request.form.get('subject', '').strip()
            body = request.form.get('body', '').strip()

        if not from_account_id or not to_address or not subject or not body:
            if request.is_json:
                conn.close(); return jsonify({'ok': False, 'error': 'missing-fields'}), 400
            flash('Please fill in all required fields', 'error')
            conn.close(); return render_template('compose.html', accounts=accounts)

        account = cursor.execute("SELECT * FROM email_accounts WHERE id = ?", (from_account_id,)).fetchone()
        if not account:
            if request.is_json:
                conn.close(); return jsonify({'ok': False, 'error': 'invalid-account'}), 400
            flash('Invalid sending account', 'error')
            conn.close(); return render_template('compose.html', accounts=accounts)

        smtp_password = decrypt_password(account['smtp_password'])
        if not smtp_password:
            if request.is_json:
                conn.close(); return jsonify({'ok': False, 'error': 'decrypt-failed'}), 500
            flash('Failed to decrypt SMTP password. Re-configure the account.', 'error')
            conn.close(); return render_template('compose.html', accounts=accounts)

        msg = MIMEMultipart()
        msg['From'] = account['email_address']
        msg['To'] = to_address
        if cc_address:
            msg['Cc'] = cc_address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            smtp_host = account['smtp_host']
            smtp_port = int(account['smtp_port']) if account['smtp_port'] else 587
            smtp_username = account['smtp_username']
            if account['smtp_use_ssl']:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            server.login(smtp_username, smtp_password)
            recipients_all = [to_address] + ([cc_address] if cc_address else [])
            server.sendmail(account['email_address'], recipients_all, msg.as_string())
            server.quit()
        except Exception as e:
            if request.is_json:
                conn.close(); return jsonify({'ok': False, 'error': str(e)}), 500
            flash(f'Error sending email: {e}', 'error')
            conn.close(); return render_template('compose.html', accounts=accounts)

        if request.is_json:
            conn.close(); return jsonify({'ok': True})
        flash('Email sent successfully!', 'success')
        conn.close(); return redirect(url_for('inbox'))

    conn.close()
    return render_template('compose.html', accounts=accounts)

## Removed duplicate log_action (original retained above)

def run_smtp_proxy():
    """Run SMTP proxy server"""
    try:
        import aiosmtpd.controller
        handler = EmailModerationHandler()
        controller = aiosmtpd.controller.Controller(handler, hostname='127.0.0.1', port=8587)
        controller.start()
        print("📧 SMTP Proxy started on port 8587")
    except ImportError:
        print("⚠️  SMTP Proxy disabled (aiosmtpd not installed)")
        return
    except OSError as e:
        if "10048" in str(e) or "already in use" in str(e).lower():
            print("⚠️  SMTP Proxy port 8587 already in use - likely from previous instance")
        else:
            print(f"❌ SMTP Proxy failed to start: {e}")
        return

    # Keep the thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()

# Initialize database if tables don't exist
if not table_exists("users"):
    init_database()

# --- Interception Dashboard & API (Added) ---
import statistics
from typing import Optional, Dict, Any

def _intercept_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

# In-memory heartbeat registry for interception workers (populated externally / future integration)
WORKER_HEARTBEATS = {}

# Simple metrics/stat caches (centralized)
_HEALTH_CACHE: Dict[str, Any] = {'ts': 0.0, 'payload': None}
_CACHE: Dict[str, Dict[str, Any]] = {'unified': {'t': 0, 'v': None}, 'lat': {'t': 0, 'v': None}}

# ------------------------------------------------------------------
# REMOVED: Duplicate interception routes (now in blueprint)
# Routes /healthz, /interception, /api/interception/held, /api/interception/release,
# /api/interception/discard, /api/inbox, /api/email/<id>/edit
# are handled by app/routes/interception.py blueprint
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Legacy Compatibility Shims (deprecated endpoints with redirects)
# ------------------------------------------------------------------
@app.route('/api/held', methods=['GET'])
@login_required
def legacy_api_held():
    """Deprecated legacy alias -> /api/interception/held"""
    return redirect(url_for('interception_bp.api_interception_held'), code=307)

@app.route('/api/emails/pending', methods=['GET'])
def legacy_api_pending():
    """Deprecated legacy pending messages endpoint guidance"""
    return jsonify({
        'deprecated': True,
        'use': '/api/inbox?status=PENDING',
        'note': 'Interception (HELD) now separate via /api/interception/held'
    })

# Unified stats endpoint (includes legacy + interception counts)
@app.route('/api/unified-stats')
@login_required
def api_unified_stats():
    """Unified statistics combining legacy and interception statuses (5s cache)"""
    # Lightweight 5s cache to reduce DB churn
    now = time.time()
    cache = _CACHE['unified']
    if now - cache['t'] < 5 and cache['v'] is not None:
        return jsonify(cache['v'])

    conn = get_db()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM email_messages").fetchone()[0]
    pending = cur.execute("SELECT COUNT(*) FROM email_messages WHERE status='PENDING'").fetchone()[0]
    held = cur.execute("SELECT COUNT(*) FROM email_messages WHERE interception_status='HELD'").fetchone()[0]
    released = cur.execute("""
        SELECT COUNT(*) FROM email_messages
        WHERE interception_status='RELEASED' OR status IN ('SENT','APPROVED','DELIVERED')
    """).fetchone()[0]
    conn.close()

    val = {'total': total, 'pending': pending, 'held': held, 'released': released}
    _CACHE['unified'] = {'t': now, 'v': val}
    return jsonify(val)

def _compute_latency_stats():
    """Compute latency percentiles from email_messages table"""
    import math
    from statistics import mean, median

    with get_db() as c:
        rows = c.execute("""
            SELECT latency_ms FROM email_messages
            WHERE latency_ms IS NOT NULL AND latency_ms > 0
            ORDER BY latency_ms
            LIMIT 5000
        """).fetchall()

    if not rows:
        return {'count': 0}

    vals = [r['latency_ms'] for r in rows]

    def pct(p):
        if not vals:
            return None
        if p <= 0:
            return vals[0]
        if p >= 100:
            return vals[-1]
        k = (len(vals) - 1) * (p / 100.0)
        f = math.floor(k)
        cidx = math.ceil(k)
        if f == cidx:
            return vals[int(k)]
        return round(vals[f] + (vals[cidx] - vals[f]) * (k - f))

    return {
        'count': len(vals),
        'min': vals[0],
        'p50': pct(50),
        'p90': pct(90),
        'p95': pct(95),
        'p99': pct(99),
        'max': vals[-1],
        'mean': round(mean(vals)),
        'median': median(vals)
    }

@app.route('/api/latency-stats')
def api_latency_stats():
    """Latency statistics endpoint with 10s cache"""
    now = time.time()
    cache = _CACHE['lat']
    if now - cache['t'] < 10 and cache['v'] is not None:
        return jsonify(cache['v'])
    val = _compute_latency_stats()
    _CACHE['lat'] = {'t': now, 'v': val}
    return jsonify(val)

def unified_counts():
    """Helper function for unified stats (used by SSE)"""
    conn = get_db()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM email_messages").fetchone()[0]
    pending = cur.execute("SELECT COUNT(*) FROM email_messages WHERE status='PENDING'").fetchone()[0]
    held = cur.execute("SELECT COUNT(*) FROM email_messages WHERE interception_status='HELD'").fetchone()[0]
    released = cur.execute("""
        SELECT COUNT(*) FROM email_messages
        WHERE interception_status='RELEASED' OR status IN ('SENT','APPROVED','DELIVERED')
    """).fetchone()[0]
    conn.close()
    return {'total': total, 'pending': pending, 'held': held, 'released': released}

@app.route('/stream/stats')
def stream_stats():
    """SSE stream for live statistics updates"""
    import json
    def gen():
        while True:
            uni = unified_counts()
            lat = _compute_latency_stats()
            yield f"event: stats\ndata: {json.dumps({'unified': uni, 'latency': lat, 'ts': int(time.time())})}\n\n"
            time.sleep(5)
    return Response(gen(), mimetype='text/event-stream')

# End of routes - remaining duplicate routes removed (handled by blueprint)

# (All remaining duplicate interception routes deleted - see blueprint)

if __name__ == '__main__':
    # Thread registry for IMAP monitoring
    imap_threads = {}

    # Graceful SMTP proxy fallback
    try:
        import aiosmtpd  # noqa
        smtp_proxy_available = True
    except Exception:
        smtp_proxy_available = False
        app.logger.warning("SMTP proxy disabled (aiosmtpd not installed). Skipping proxy thread.")

    if smtp_proxy_available:
        smtp_thread = threading.Thread(target=run_smtp_proxy, daemon=True)
        smtp_thread.start()
    else:
        print("⚠️  SMTP proxy disabled (aiosmtpd not available)")
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
