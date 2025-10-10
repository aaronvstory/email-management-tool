"""Account Management Blueprint - Phase 1B Route Modularization

Extracted from simple_app.py lines 877-1760
Routes: /accounts, /accounts/add, /api/accounts/*, /api/detect-email-settings, /api/test-connection
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
import sqlite3
import imaplib
import smtplib
import json
from app.utils.db import DB_PATH, get_db
from app.utils.crypto import encrypt_credential, decrypt_credential

accounts_bp = Blueprint('accounts', __name__)

def _detect_email_settings(email_address: str) -> dict:
    """Smart detection of SMTP/IMAP settings based on email domain."""
    domain = email_address.split('@')[-1].lower() if '@' in email_address else ''
    providers = {
        'gmail.com': {
            'smtp_host': 'smtp.gmail.com', 'smtp_port': 587, 'smtp_use_ssl': False,
            'imap_host': 'imap.gmail.com', 'imap_port': 993, 'imap_use_ssl': True
        },
        'corrinbox.com': {
            'smtp_host': 'smtp.hostinger.com', 'smtp_port': 465, 'smtp_use_ssl': True,
            'imap_host': 'imap.hostinger.com', 'imap_port': 993, 'imap_use_ssl': True
        },
        'outlook.com': {
            'smtp_host': 'smtp-mail.outlook.com', 'smtp_port': 587, 'smtp_use_ssl': False,
            'imap_host': 'outlook.office365.com', 'imap_port': 993, 'imap_use_ssl': True
        },
        'hotmail.com': {
            'smtp_host': 'smtp-mail.outlook.com', 'smtp_port': 587, 'smtp_use_ssl': False,
            'imap_host': 'outlook.office365.com', 'imap_port': 993, 'imap_use_ssl': True
        },
        'yahoo.com': {
            'smtp_host': 'smtp.mail.yahoo.com', 'smtp_port': 465, 'smtp_use_ssl': True,
            'imap_host': 'imap.mail.yahoo.com', 'imap_port': 993, 'imap_use_ssl': True
        },
    }
    if domain in providers:
        return providers[domain]
    return {
        'smtp_host': f'smtp.{domain}', 'smtp_port': 587, 'smtp_use_ssl': False,
        'imap_host': f'imap.{domain}', 'imap_port': 993, 'imap_use_ssl': True,
    }


def _test_email_connection(kind: str, host: str, port: int, username: str, password: str, use_ssl: bool):
    """Lightweight connectivity test for IMAP/SMTP."""
    if not host or not port or not username:
        return False, "Missing connection parameters"
    try:
        if kind.lower() == 'imap':
            client = imaplib.IMAP4_SSL(host, int(port)) if use_ssl else imaplib.IMAP4(host, int(port))
            if password:
                client.login(username, password)
            client.logout()
            return True, f"IMAP OK {host}:{port}"
        if kind.lower() == 'smtp':
            if use_ssl and int(port) == 465:
                server = smtplib.SMTP_SSL(host, int(port), timeout=10)
            else:
                server = smtplib.SMTP(host, int(port), timeout=10)
                server.starttls()
            if password:
                server.login(username, password)
            server.quit()
            return True, f"SMTP OK {host}:{port}"
        return False, f"Unsupported kind {kind}"
    except Exception as e:
        return False, str(e)


@accounts_bp.route('/accounts')
@login_required
def email_accounts():
    """Email accounts management page with enhanced status monitoring"""
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard.dashboard'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    accounts = cursor.execute(
        """
        SELECT id, account_name, email_address,
               imap_host, imap_port, imap_username, imap_use_ssl,
               smtp_host, smtp_port, smtp_username, smtp_use_ssl,
               is_active, last_checked, last_error,
               created_at, updated_at
        FROM email_accounts
        ORDER BY account_name
        """
    ).fetchall()

    conn.close()

    import os
    template_path = os.path.join(current_app.template_folder, 'accounts_simple.html')
    if os.path.exists(template_path):
        return render_template('accounts_simple.html', accounts=accounts)
    else:
        accounts_dict = {acc['id']: dict(acc) for acc in accounts}
        return render_template('accounts.html', accounts=accounts_dict)


@accounts_bp.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def add_email_account():
    """Add new email account"""
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        account_name = request.form.get('account_name')
        email_address = request.form.get('email_address')

        use_auto_detect = request.form.get('use_auto_detect') == 'on'
        if use_auto_detect and email_address:
            auto = _detect_email_settings(email_address)
            imap_host = auto['imap_host']; imap_port = auto['imap_port']; imap_use_ssl = auto['imap_use_ssl']
            smtp_host = auto['smtp_host']; smtp_port = auto['smtp_port']; smtp_use_ssl = auto['smtp_use_ssl']
            imap_username = email_address; smtp_username = email_address
            imap_password = request.form.get('imap_password'); smtp_password = request.form.get('smtp_password')
        else:
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

        imap_ok, imap_msg = _test_email_connection('imap', imap_host, imap_port, imap_username, imap_password, imap_use_ssl)
        smtp_ok, smtp_msg = _test_email_connection('smtp', smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl)

        if not imap_ok:
            flash(f'IMAP connection failed: {imap_msg}', 'error')
            return render_template('add_account.html')
        if not smtp_ok:
            flash(f'SMTP connection failed: {smtp_msg}', 'error')
            return render_template('add_account.html')

        encrypted_imap_password = encrypt_credential(imap_password)
        encrypted_smtp_password = encrypt_credential(smtp_password)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO email_accounts
            (account_name, email_address, imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
             smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                account_name, email_address, imap_host, imap_port, imap_username, encrypted_imap_password, imap_use_ssl,
                smtp_host, smtp_port, smtp_username, encrypted_smtp_password, smtp_use_ssl,
            ),
        )
        account_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Try to start IMAP watcher for the new account (best effort)
        try:
            from simple_app import monitor_imap_account, imap_threads  # lazy import to avoid circular at import time
            import threading
            thread = threading.Thread(target=monitor_imap_account, args=(account_id,), daemon=True)
            imap_threads[account_id] = thread
            thread.start()
        except Exception as e:
            # Silent failure pattern as in original; log for visibility
            try:
                current_app.logger.warning(f"Failed to start IMAP monitor thread for account {account_id}: {e}")
            except Exception:
                pass

        flash('Account added successfully', 'success')
        return redirect(url_for('accounts.email_accounts'))

    return render_template('add_account.html')

@accounts_bp.route('/api/detect-email-settings', methods=['POST'])
@login_required
def api_detect_email_settings():
    """API endpoint for smart detection of email settings (moved from monolith)."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '')

    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400

    settings = _detect_email_settings(email)
    return jsonify(settings)

