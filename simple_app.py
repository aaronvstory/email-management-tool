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
from email.utils import formatdate, make_msgid, parsedate_to_datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Blueprint registration
from app.routes.interception import bp_interception
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.stats import stats_bp
from app.routes.moderation import moderation_bp
from app.routes.compose import compose_bp
from app.routes.inbox import inbox_bp
from app.routes.accounts import accounts_bp
from app.routes.emails import emails_bp
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
from app.utils.db import get_db, DB_PATH, table_exists, fetch_counts

# Import IMAP watcher for email interception
from app.services.imap_watcher import ImapWatcher, AccountConfig

# -----------------------------------------------------------------------------
# Minimal re-initialization (original file trimmed during refactor)
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'  # Updated for blueprint namespacing

# Import SimpleUser for Flask-Login (Phase 1B modularization)
from app.models.simple_user import SimpleUser, load_user_from_db

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login session management"""
    return load_user_from_db(user_id)

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

def _imap_connect_account(account_row):
    """Connect to IMAP account and return (imap_obj, supports_move)"""
    host = account_row['imap_host']
    port = int(account_row['imap_port'] or 993)
    username = account_row['imap_username']
    password = decrypt_credential(account_row['imap_password'])
    if not (host and username and password):
        raise RuntimeError("Missing IMAP credentials")
    if port == 993:
        imap_obj = imaplib.IMAP4_SSL(host, port)
    else:
        imap_obj = imaplib.IMAP4(host, port)
        try:
            imap_obj.starttls()
        except Exception:
            pass
    imap_obj.login(username, password)
    try:
        typ, caps = imap_obj.capability()
        supports_move = any(b'MOVE' in c.upper() for c in caps) if isinstance(caps, list) else False
    except Exception:
        supports_move = False
    return imap_obj, supports_move

def _ensure_quarantine(imap_obj, folder_name="Quarantine"):
    """Ensure quarantine folder exists"""
    try:
        imap_obj.create(folder_name)
    except Exception:
        pass

def _move_uid_to_quarantine(imap_obj, uid, quarantine="Quarantine"):
    """Move message to quarantine using MOVE or COPY+DELETE fallback"""
    _ensure_quarantine(imap_obj, quarantine)
    # Try native MOVE
    try:
        typ, _ = imap_obj.uid('MOVE', uid, quarantine)
        if typ == 'OK':
            return True
    except Exception:
        pass
    # Fallback: COPY + delete
    try:
        typ, _ = imap_obj.uid('COPY', uid, quarantine)
        if typ == 'OK':
            imap_obj.uid('STORE', uid, '+FLAGS', r'(\Deleted)')
            imap_obj.expunge()
            return True
    except Exception:
        pass
    return False

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

# Register blueprints (Phase 1B modularization)
app.register_blueprint(auth_bp)          # Auth routes: /, /login, /logout
app.register_blueprint(dashboard_bp)     # Dashboard routes: /dashboard, /dashboard/<tab>
app.register_blueprint(stats_bp)         # Stats API: /api/stats, /api/unified-stats, /stream/stats
app.register_blueprint(moderation_bp)    # Moderation: /rules
app.register_blueprint(bp_interception)  # Interception API (Phase 1A)
app.register_blueprint(compose_bp)       # Compose: /compose (Phase 1C)
app.register_blueprint(inbox_bp)         # Inbox: /inbox (Phase 1C)
app.register_blueprint(accounts_bp)      # Accounts pages: /accounts, /accounts/add (Phase 1C)
app.register_blueprint(emails_bp)        # Email queue + viewer: /emails, /email/<id> (Phase 1C)

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

            # Lookup account_id by matching recipient email addresses
            account_id = None
            rcpt_list = [str(r) for r in envelope.rcpt_tos]
            if rcpt_list:
                try:
                    conn_match = sqlite3.connect(DB_PATH)
                    curm = conn_match.cursor()
                    placeholders = ",".join("?" for _ in rcpt_list)
                    rows = curm.execute(
                        f"SELECT id FROM email_accounts WHERE lower(email_address) IN ({placeholders})",
                        [r.lower() for r in rcpt_list]
                    ).fetchall()
                    if rows:
                        account_id = rows[0][0]
                    conn_match.close()
                except Exception:
                    pass

            # Store in database with retry logic
            print(f"📨 SMTP Handler: Storing in database - Subject: {subject}, Risk: {risk_score}, Account: {account_id}")

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=10.0)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO email_messages
                        (message_id, account_id, direction, status, interception_status,
                         sender, recipients, subject, body_text, body_html,
                         raw_content, keywords_matched, risk_score, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ''', (
                        message_id,
                        account_id,
                        'inbound',
                        'PENDING',
                        'HELD',
                        sender,
                        recipients,
                        subject,
                        body_text,
                        body_html,
                        envelope.content,
                        json.dumps(keywords_matched),
                        risk_score
                    ))
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

# Removed duplicate blueprint registration
# if 'app' in globals() and bp_interception:
#     try:
#         app.register_blueprint(bp_interception)
#     except Exception:
#         pass

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
# ============================================================================
# PHASE 1B: Auth routes migrated to app/routes/auth.py
# Routes: /, /login, /logout
# ============================================================================

# ============================================================================
# PHASE 1B: Dashboard routes migrated to app/routes/dashboard.py
# Routes: /dashboard, /dashboard/<tab>, /test-dashboard
# ============================================================================

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

"""Moved: /emails queue page → app/routes/emails.py (emails_bp)"""

"""Moved: /email/<id> viewer page → app/routes/emails.py (emails_bp)"""

"""Moved: /email/<id>/action → app/routes/emails.py (emails_bp)"""

# ============================================================================
# PHASE 1B: Moderation routes migrated to app/routes/moderation.py
# Routes: /rules
# ============================================================================

# Moved: /accounts page → app/routes/accounts.py (accounts_bp)

# Moved: /api/detect-email-settings → app/routes/accounts.py (accounts_bp)

# Moved: /accounts/add page → app/routes/accounts.py (accounts_bp)

# ============================================================================
# PHASE 1B: Stats routes migrated to app/routes/stats.py
# Routes: /api/stats, /api/unified-stats, /api/latency-stats, /stream/stats
# ============================================================================

@app.route('/api/events')
@login_required
def api_events():
    """Server-Sent Events endpoint for real-time updates"""
    def generate():
        while True:
            # TODO: introduce in-memory cache layer (ttl ~2s) using a simple dict + timestamps
            # Get latest email count
            counts = fetch_counts()
            pending = counts.get('pending', 0)

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

# ============================================================================
# /api/inbox route removed - now provided by interception blueprint
# See app/routes/interception.py for the canonical implementation
# ============================================================================

@app.route('/api/fetch-emails', methods=['POST'])
@login_required
def api_fetch_emails():
    """Fetch emails from IMAP server using UID-based fetching"""
    data = request.get_json() or {}
    account_id = data.get('account_id')
    fetch_count = int(data.get('count', 20))
    offset = int(data.get('offset', 0))

    if not account_id:
        return jsonify({'success': False, 'error': 'Account ID required'}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    acct = cur.execute(
        "SELECT * FROM email_accounts WHERE id=? AND is_active=1",
        (account_id,)
    ).fetchone()
    if not acct:
        conn.close()
        return jsonify({'success': False, 'error': 'Account not found'}), 404

    mail = None
    try:
        password = decrypt_credential(acct['imap_password'])
        if not password:
            conn.close()
            return jsonify({'success': False, 'error': 'Password decrypt failed'}), 500

        if acct['imap_port'] == 993:
            mail = imaplib.IMAP4_SSL(acct['imap_host'], acct['imap_port'])
        else:
            mail = imaplib.IMAP4(acct['imap_host'], acct['imap_port'])
            try:
                mail.starttls()
            except Exception:
                pass

        mail.login(acct['imap_username'], password)
        mail.select('INBOX')

        typ, data = mail.uid('search', None, 'ALL')
        if typ != 'OK':
            return jsonify({'success': False, 'error': 'UID SEARCH failed'}), 500

        uid_bytes = data[0].split() if data and data[0] else []
        total = len(uid_bytes)
        start = max(0, total - offset - fetch_count)
        end = total - offset
        window = uid_bytes[start:end][-fetch_count:]

        results = []
        for raw_uid in reversed(window):
            uid = raw_uid.decode()
            typ, msg_payload = mail.uid('fetch', uid, '(RFC822 INTERNALDATE)')
            if typ != 'OK' or not msg_payload or msg_payload[0] is None:
                continue

            # Extract raw email and INTERNALDATE from IMAP response
            raw_email = msg_payload[0][1]
            msg = message_from_bytes(raw_email, policy=policy.default)

            # Parse INTERNALDATE from IMAP response (more reliable than Date header)
            internaldate = None
            try:
                # IMAP response format: msg_payload[0][0] contains flags and INTERNALDATE
                fetch_data = msg_payload[0][0]
                if isinstance(fetch_data, bytes):
                    fetch_str = fetch_data.decode('utf-8', errors='ignore')
                    # Extract INTERNALDATE from response like: b'1 (RFC822 {1234} INTERNALDATE "01-Jan-2025 12:00:00 +0000")'
                    import re
                    match = re.search(r'INTERNALDATE "([^"]+)"', fetch_str)
                    if match:
                        date_str = match.group(1)
                        date_tuple = imaplib.Internaldate2tuple(f'INTERNALDATE "{date_str}"'.encode())
                        if date_tuple:
                            from datetime import datetime as dt
                            internaldate = dt(*date_tuple[:6]).isoformat()
            except Exception:
                pass

            # Fallback to Date header if INTERNALDATE parsing failed
            if not internaldate:
                try:
                    date_hdr = msg.get('Date')
                    if date_hdr:
                        internaldate = parsedate_to_datetime(date_hdr).isoformat()
                except Exception:
                    pass

            message_id = msg.get('Message-ID') or f"fetch_{account_id}_{uid}"
            sender = msg.get('From', '')
            subject = msg.get('Subject', 'No Subject')
            recipients = json.dumps([msg.get('To', '')])

            body_text = ''
            body_html = ''
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    if ctype == 'text/plain':
                        body_text = payload.decode('utf-8', errors='ignore')
                    elif ctype == 'text/html':
                        body_html = payload.decode('utf-8', errors='ignore')
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode('utf-8', errors='ignore')

            cur.execute("""
                INSERT OR IGNORE INTO email_messages
                (message_id, sender, recipients, subject, body_text, body_html,
                 raw_content, account_id, direction, interception_status,
                 original_uid, original_internaldate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                message_id, sender, recipients, subject, body_text, body_html,
                raw_email, account_id, 'inbound', 'FETCHED', uid, internaldate
            ))

            row = cur.execute(
                "SELECT id FROM email_messages WHERE message_id=? ORDER BY id DESC LIMIT 1",
                (message_id,)
            ).fetchone()
            results.append({
                'id': row['id'] if row else None,
                'message_id': message_id,
                'uid': uid,
                'subject': subject
            })

        conn.commit()
        return jsonify({'success': True, 'total_available': total, 'fetched': len(results), 'emails': results})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass
        conn.close()

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
    """Manually intercept an email with remote MOVE to Quarantine folder"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute("""
        SELECT em.*, ea.imap_host, ea.imap_port, ea.imap_username, ea.imap_password
        FROM email_messages em
        LEFT JOIN email_accounts ea ON em.account_id = ea.id
        WHERE em.id=?
    """, (email_id,)).fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Not found'}), 404
    if not row['account_id']:
        conn.close()
        return jsonify({'success': False, 'error': 'No linked account'}), 400

    previous = row['interception_status']
    remote_move = False
    note = None

    if previous != 'HELD':
        try:
            imap_obj, _supports_move = _imap_connect_account(row)
            imap_obj.select('INBOX')
            uid = row['original_uid']

            if not uid and row['message_id']:
                crit = f'(HEADER Message-ID "{row["message_id"]}")'
                typ, data = imap_obj.uid('search', None, crit)
                if typ == 'OK' and data and data[0]:
                    found = data[0].split()
                    if found:
                        uid = found[-1].decode()

            if not uid and row['subject']:
                subj = row['subject'].replace('"', '')
                typ, data = imap_obj.uid('search', None, f'(HEADER Subject "{subj}")')
                if typ == 'OK' and data and data[0]:
                    found = data[0].split()
                    if found:
                        uid = found[-1].decode()

            if uid:
                remote_move = _move_uid_to_quarantine(imap_obj, uid)
                if remote_move and not row['original_uid']:
                    cur.execute(
                        "UPDATE email_messages SET original_uid=? WHERE id=?",
                        (uid, email_id)
                    )
            else:
                note = "Remote UID not found (Message-ID/Subject search failed)"
            imap_obj.logout()
        except Exception as exc:
            note = f"IMAP error: {exc}"

    cur.execute("""
        UPDATE email_messages
        SET interception_status='HELD',
            status='PENDING',
            quarantine_folder='Quarantine',
            action_taken_at=datetime('now')
        WHERE id=?
    """, (email_id,))
    conn.commit()

    # Calculate and update latency_ms if not already set
    try:
        row_t = cur.execute("""
            SELECT created_at, action_taken_at, latency_ms
            FROM email_messages
            WHERE id=?
        """, (email_id,)).fetchone()

        if row_t and row_t['created_at'] and row_t['action_taken_at'] and row_t['latency_ms'] is None:
            cur.execute("""
                UPDATE email_messages
                SET latency_ms = CAST((julianday(action_taken_at) - julianday(created_at)) * 86400000 AS INTEGER)
                WHERE id=?
            """, (email_id,))
            conn.commit()
    except Exception as e:
        # Best-effort latency calculation, don't fail the whole operation
        print(f"Warning: Could not calculate latency_ms: {e}")

    conn.close()

    # Audit log the manual interception action
    try:
        from app.services.audit import log_action
        user_id = getattr(current_user, 'id', None)
        details = f"Manual intercept: remote_move={remote_move}, previous_status={previous}"
        if note:
            details += f", note={note}"
        log_action('MANUAL_INTERCEPT', user_id, email_id, details)
    except Exception as e:
        # Best-effort logging, don't fail the operation
        print(f"Warning: Could not log audit action: {e}")

    return jsonify({
        'success': True,
        'email_id': email_id,
        'remote_move': remote_move,
        'previous_status': previous,
        'note': note
    })

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
        return redirect(url_for('dashboard.dashboard', tab='diagnostics') + f'?account_id={account_id}')
    else:
        return redirect(url_for('dashboard.dashboard', tab='diagnostics'))

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

# ===== LEGACY_REMOVED: legacy edit/review endpoints superseded by interception blueprint =====
# @app.route('/email/<int:email_id>/edit', methods=['GET', 'POST'])
# def edit_email(...): ...
# @app.route('/email/<int:email_id>/save', methods=['POST'])
# def save_email_draft(...): ...
# @app.route('/email/<int:email_id>/approve-send', methods=['POST'])
# def approve_and_send_email(...): ...
# @app.route('/email/<int:email_id>/reject', methods=['POST'])
# def reject_email(...): ...

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

# (Functions removed - see LEGACY_REMOVED comment block above)

# Moved: /inbox page → app/routes/inbox.py (inbox_bp)

# (Compose routes migrated to app/routes/compose.py)

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

# Note: /api/unified-stats, /api/latency-stats, and /stream/stats
# migrated to app/routes/stats.py (see Phase 1B marker above)

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

    # Start IMAP monitoring threads (delegated to worker module)
    from app.workers.imap_startup import start_imap_watchers
    watchers_started = start_imap_watchers(monitor_imap_account, imap_threads, app.logger)

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
