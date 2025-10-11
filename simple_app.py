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
from dotenv import load_dotenv
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
from app.routes.diagnostics import diagnostics_bp
from app.routes.legacy import legacy_bp
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


def check_port_available(port, host='localhost'):
    """Check if a port is available without psutil"""
    import socket
    import subprocess
    import platform

    # First check if port is in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    sock.close()

    if result != 0:  # Port is free
        return True, None

    # Port is in use, try to find and kill the process
    if platform.system() == 'Windows':
        # Windows: use netstat
        try:
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
            for line in output.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    try:
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
                        print(f"Killed process {pid} using port {port}")
                        time.sleep(2)
                        return True, pid
                    except:
                        pass
        except:
            pass
    else:
        # Linux/Mac: use lsof
        try:
            output = subprocess.check_output(f'lsof -i :{port}', shell=True, text=True)
            lines = output.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) > 1:
                    pid = parts[1]
                    try:
                        subprocess.run(f'kill -9 {pid}', shell=True, check=True)
                        print(f"Killed process {pid} using port {port}")
                        time.sleep(2)
                        return True, pid
                    except:
                        pass
        except:
            pass

    return False, None

# Load environment from .env early
load_dotenv()

app = Flask(__name__)

# Ensure backup directory exists
import os
os.makedirs("database_backups", exist_ok=True)
os.makedirs("emergency_email_backup", exist_ok=True)
# Security: SECRET_KEY from environment (never hardcode in production)
app.config['SECRET_KEY'] = (
    os.environ.get('FLASK_SECRET_KEY')
    or os.environ.get('SECRET_KEY')
    or os.environ.get('FLASK_SECRET')
    or 'dev-secret-change-in-production'
)

# CSRF + Rate Limiting (use shared extension instances)
try:
    from flask_wtf.csrf import generate_csrf, CSRFError  # type: ignore[import]
except Exception:
    def generate_csrf() -> str:  # type: ignore[misc]
        return ""
    class CSRFError(Exception):  # type: ignore[misc]
        pass
from app.extensions import csrf, limiter

# Bind extensions to app
csrf.init_app(app)
limiter.init_app(app)

# CSRF configuration - time-limited tokens and allow HTTP in dev
app.config['WTF_CSRF_TIME_LIMIT'] = 7200  # 2 hours; rotate token periodically
app.config['WTF_CSRF_SSL_STRICT'] = False  # Set True in production when HTTPS is enforced

# SECRET_KEY validation: prevent accidental weak/default secret in production
_default_secret = 'dev-secret-change-in-production'
secret = app.config.get('SECRET_KEY')
if (not app.debug) and (not secret or secret == _default_secret or len(str(secret)) < 32):
    raise RuntimeError("SECURITY: A strong SECRET_KEY is required in production. Set FLASK_SECRET_KEY.")
if app.debug and (not secret or secret == _default_secret):
    try:
        app.logger.warning("SECURITY: Using development SECRET_KEY; do not use in production.")
    except Exception:
        pass

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

# Import email helper functions (Phase 3: Helper Consolidation)
from app.utils.email_helpers import detect_email_settings, test_email_connection

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

    # Worker heartbeats (observability)
    cur.execute("""CREATE TABLE IF NOT EXISTS worker_heartbeats(
        worker_id TEXT PRIMARY KEY,
        last_heartbeat TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT
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
app.register_blueprint(diagnostics_bp)   # Diagnostics & tests
app.register_blueprint(legacy_bp)        # Legacy compatibility routes

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

# Context processor to inject pending_count and csrf_token into all templates
@app.context_processor
def inject_template_context():
    """Inject pending_count and csrf_token into all templates"""
    from typing import Dict, Any
    context: Dict[str, Any] = {'pending_count': 0}

    # Add pending count for authenticated users
    try:
        if current_user.is_authenticated:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            pending_count = cursor.execute("SELECT COUNT(*) FROM email_messages WHERE status = 'PENDING'").fetchone()[0]
            conn.close()
            context['pending_count'] = pending_count
    except:
        pass

    # Add CSRF token
    context['csrf_token'] = generate_csrf

    return context

# User-friendly error handlers for security events
@app.errorhandler(CSRFError)
def handle_csrf_exception(e):
    """Explicit Flask-WTF CSRF error handler"""
    if request.is_json:
        return jsonify({'error': 'Security token expired. Please refresh the page.'}), 400
    flash('Your session has expired. Please try again.', 'error')
    return redirect(url_for('auth.login'))

@app.errorhandler(400)
def csrf_error(e):
    """Handle CSRF validation failures with user-friendly message"""
    error_str = str(e)
    if 'CSRF' in error_str or 'token' in error_str.lower():
        if request.is_json:
            return jsonify({'error': 'Security token expired. Please refresh the page.'}), 400
        flash('Your session has expired. Please try again.', 'error')
        return redirect(url_for('auth.login'))
    return jsonify({'error': error_str}), 400


@app.errorhandler(429)
def ratelimit_error(e):
    """Handle rate limit exceeded with user-friendly message"""
    if request.is_json:
        return jsonify({'error': 'Too many requests. Please wait a moment and try again.'}), 429
    flash('Too many login attempts. Please wait a minute and try again.', 'warning')
    return redirect(url_for('auth.login'))


@app.after_request
def log_security_events(response):
    """Log CSRF failures and rate limit violations for security monitoring"""
    try:
        if response.status_code == 400:
            response_text = response.get_data(as_text=True)
            if 'CSRF' in response_text or 'token' in response_text.lower():
                app.logger.warning(f"CSRF validation failed: {request.method} {request.url} from {request.remote_addr}")
        elif response.status_code == 429:
            app.logger.warning(f"Rate limit exceeded: {request.method} {request.url} from {request.remote_addr}")
    except Exception:
        try:
            app.logger.exception("Security event logging failed")
        except Exception:
            pass
    return response

# Routes
# ============================================================================
# PHASE 1B: Auth routes migrated to app/routes/auth.py
# Routes: /, /login, /logout
# ============================================================================

# ============================================================================
# PHASE 1B: Dashboard routes migrated to app/routes/dashboard.py
# Routes: /dashboard, /dashboard/<tab>, /test-dashboard
# ============================================================================

"""Moved: /test/cross-account and /api/test-status -> diagnostics blueprint"""

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

"""Moved: diagnostics & test routes -> diagnostics blueprint"""

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
        smtp_host = os.environ.get('SMTP_PROXY_HOST', '127.0.0.1')
        smtp_port = int(os.environ.get('SMTP_PROXY_PORT', '8587'))
        controller = aiosmtpd.controller.Controller(handler, hostname=smtp_host, port=smtp_port)
        controller.start()
        print(f"📧 SMTP Proxy started on {smtp_host}:{smtp_port}")
        # Self-check: send a lightweight message through the proxy to verify accept path
        try:
            subj = f"[SC] SMTP Self-Check {int(time.time())}"
            msg = MIMEText('ok')
            msg['Subject'] = subj
            msg['From'] = 'selfcheck@localhost'
            msg['To'] = 'selfcheck@localhost'
            s = smtplib.SMTP(smtp_host, smtp_port, timeout=3)
            s.send_message(msg)
            try:
                s.quit()
            except Exception:
                pass
            # Record last successful self-check timestamp
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS system_status (key TEXT PRIMARY KEY, value TEXT)")
                cur.execute("INSERT OR REPLACE INTO system_status(key, value) VALUES('smtp_last_selfcheck', datetime('now'))")
                conn.commit(); conn.close()
            except Exception:
                pass
        except Exception:
            # Best-effort only; do not crash proxy thread
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS system_status (key TEXT PRIMARY KEY, value TEXT)")
                cur.execute("INSERT OR REPLACE INTO system_status(key, value) VALUES('smtp_last_selfcheck', NULL)")
                conn.commit(); conn.close()
            except Exception:
                pass
    except ImportError:
        print("⚠️  SMTP Proxy disabled (aiosmtpd not installed)")
        return
    except OSError as e:
        if "10048" in str(e) or "already in use" in str(e).lower():
            print("⚠️  SMTP Proxy port already in use - likely from previous instance")
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
"""Legacy compatibility routes moved to app/routes/legacy.py"""

# Note: /api/unified-stats, /api/latency-stats, and /stream/stats
# migrated to app/routes/stats.py (see Phase 1B marker above)

# End of routes - remaining duplicate routes removed (handled by blueprint)

# (All remaining duplicate interception routes deleted - see blueprint)



def cleanup_emergency_backups(days_to_keep=7):
    """Clean up old emergency email backups"""
    import os
    import time
    import json
    from datetime import datetime, timedelta

    emergency_dir = "emergency_email_backup"
    if not os.path.exists(emergency_dir):
        return

    cutoff_time = time.time() - (days_to_keep * 86400)

    for filename in os.listdir(emergency_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(emergency_dir, filename)
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    print(f"Cleaned up old backup: {filename}")
                except:
                    pass

# Schedule cleanup to run periodically
def schedule_cleanup():
    import threading
    def run_cleanup():
        while True:
            cleanup_emergency_backups()
            time.sleep(86400)  # Run daily

    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()


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
    smtp_host = os.environ.get('SMTP_PROXY_HOST', '127.0.0.1')
    smtp_port = int(os.environ.get('SMTP_PROXY_PORT', '8587'))
    flask_host = os.environ.get('FLASK_HOST', '127.0.0.1')
    flask_port = int(os.environ.get('FLASK_PORT', '5000'))
    print(f"   📧 SMTP Proxy: {smtp_host}:{smtp_port}")
    print(f"   🌐 Web Dashboard: http://{flask_host}:{flask_port}")
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
    debug = str(os.environ.get('FLASK_DEBUG', '1')).lower() in ('1', 'true', 'yes')
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    app.run(debug=debug, use_reloader=False, host=host, port=port)
