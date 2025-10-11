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

# Import IMAP helper functions
from app.utils.imap_helpers import _imap_connect_account, _ensure_quarantine, _move_uid_to_quarantine

# Import IMAP watcher for email interception
from app.services.imap_watcher import ImapWatcher, AccountConfig

# -----------------------------------------------------------------------------
# Minimal re-initialization (original file trimmed during refactor)
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'  # type: ignore[reportAttributeAccessIssue]

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
                if not password:
                    raise RuntimeError("Missing decrypted IMAP password for account")

                # Create account configuration with account_id and db_path
                pwd: str = password  # type: ignore[assignment]
                cfg = AccountConfig(
                    imap_host=row['imap_host'],
                    imap_port=row['imap_port'] or 993,
                    username=row['imap_username'],
                    password=pwd,
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
                    ctype = part.get_content_type()
                    payload = part.get_payload(decode=True)
                    if ctype == "text/plain":
                        if isinstance(payload, (bytes, bytearray)):
                            body_text = payload.decode('utf-8', errors='ignore')
                        elif isinstance(payload, str):
                            body_text = payload
                    elif ctype == "text/html":
                        if isinstance(payload, (bytes, bytearray)):
                            body_html = payload.decode('utf-8', errors='ignore')
                        elif isinstance(payload, str):
                            body_html = payload
            else:
                payload = email_msg.get_payload(decode=True)
                if isinstance(payload, (bytes, bytearray)):
                    body_text = payload.decode('utf-8', errors='ignore')
                elif isinstance(payload, str):
                    body_text = payload

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

# Moved: /api/events -> stats blueprint (app/routes/stats.py)

# Moved: /api/diagnostics/<account_id> -> accounts blueprint

# Moved: /api/accounts -> accounts blueprint

# ============================================================================
# /api/inbox route removed - now provided by interception blueprint
# See app/routes/interception.py for the canonical implementation
# ============================================================================

# Moved: /api/fetch-emails -> emails blueprint

# Moved: /api/email/<id>/reply-forward -> emails blueprint

# Moved: /api/email/<id>/download -> emails blueprint

# Moved: /api/email/<id>/intercept -> interception blueprint

# Moved: /api/accounts/<id>/health -> accounts blueprint

# Moved: /api/accounts/<id>/test -> accounts blueprint

# Moved: /api/accounts/<id> (CRUD) -> accounts blueprint

# Moved: /api/accounts/export -> accounts blueprint

# Removed: /api/accounts/<int:account_id> (duplicate/unsafe testing route)

# Moved: /api/test-connection/<type> -> accounts blueprint

# Moved: /diagnostics pages -> accounts blueprint

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

# Moved: /email/<int:id>/full -> emails blueprint

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
