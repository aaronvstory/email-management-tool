"""Account Management Blueprint - Phase 1B Route Modularization

Extracted from simple_app.py lines 877-1760
Routes: /accounts, /accounts/add, /api/accounts/*, /api/detect-email-settings, /api/test-connection
Phase 3: Consolidated email helpers - using app.utils.email_helpers
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
import sqlite3
import json
from app.utils.db import DB_PATH, get_db
from datetime import datetime
from app.utils.crypto import encrypt_credential, decrypt_credential
from app.extensions import limiter

# Phase 3: Import consolidated email helpers
from app.utils.email_helpers import detect_email_settings as _detect_email_settings, test_email_connection as _test_email_connection

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/api/accounts')
@login_required
def api_get_accounts():
    """Get all email accounts (admin and diagnostics)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute(
        """
        SELECT id, account_name, email_address, is_active,
               smtp_host, smtp_port, imap_host, imap_port
        FROM email_accounts
        ORDER BY account_name
        """
    ).fetchall()
    conn.close()
    return jsonify({'success': True, 'accounts': [dict(r) for r in rows]})


@accounts_bp.route('/api/accounts/<account_id>/health')
@login_required
def api_account_health(account_id):
    """Get real-time health status for an account (from DB fields)."""
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    account = cur.execute(
        """
        SELECT smtp_health_status, imap_health_status,
               last_health_check, last_error, connection_status
        FROM email_accounts WHERE id = ?
        """,
        (account_id,),
    ).fetchone()
    if not account:
        conn.close(); return jsonify({'error': 'Account not found'}), 404
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


@accounts_bp.route('/api/accounts/<account_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_account_crud(account_id):
    """Account CRUD operations (sanitized; no decrypted secrets returned)."""
    if request.method == 'GET':
        conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
        cur = conn.cursor(); acc = cur.execute("SELECT * FROM email_accounts WHERE id=?", (account_id,)).fetchone()
        if not acc:
            conn.close(); return jsonify({'error': 'Account not found'}), 404
        data = dict(acc); data.pop('imap_password', None); data.pop('smtp_password', None)
        conn.close(); return jsonify(data)

    if request.method == 'PUT':
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        payload = request.get_json(silent=True) or {}
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        fields, values = [], []
        for field in ['account_name','email_address','provider_type','smtp_host','smtp_port','smtp_username','imap_host','imap_port','imap_username']:
            if field in payload:
                fields.append(f"{field} = ?"); values.append(payload[field])
        if payload.get('smtp_password'):
            fields.append('smtp_password = ?'); values.append(encrypt_credential(payload['smtp_password']))
        if payload.get('imap_password'):
            fields.append('imap_password = ?'); values.append(encrypt_credential(payload['imap_password']))
        if 'smtp_use_ssl' in payload:
            fields.append('smtp_use_ssl = ?'); values.append(1 if payload['smtp_use_ssl'] else 0)
        if 'imap_use_ssl' in payload:
            fields.append('imap_use_ssl = ?'); values.append(1 if payload['imap_use_ssl'] else 0)
        if 'is_active' in payload:
            # Guard: cannot activate without valid (decrypted, non-empty) credentials
            desired_active = 1 if (payload['is_active'] in (1, True, '1')) else 0
            if desired_active:
                existing = cur.execute(
                    "SELECT imap_username, smtp_username, imap_password, smtp_password FROM email_accounts WHERE id=?",
                    (account_id,)
                ).fetchone()
                if not existing or not existing[0] or not existing[1]:
                    conn.close(); return jsonify({'error': 'Cannot activate account without credentials'}), 400
                from app.utils.crypto import decrypt_credential as _dec
                imap_pwd = _dec(existing[2]) if existing[2] else None
                smtp_pwd = _dec(existing[3]) if existing[3] else None
                if not imap_pwd or not smtp_pwd:
                    conn.close(); return jsonify({'error': 'Cannot activate: credentials invalid or missing'}), 400
            fields.append('is_active = ?'); values.append(desired_active)
        if fields:
            fields.append('updated_at = CURRENT_TIMESTAMP'); values.append(account_id)
            cur.execute(f"UPDATE email_accounts SET {', '.join(fields)} WHERE id = ?", values); conn.commit()
        conn.close(); return jsonify({'success': True})

    # DELETE
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("DELETE FROM email_accounts WHERE id=?", (account_id,)); conn.commit(); conn.close()
    return jsonify({'success': True})


@accounts_bp.route('/api/accounts/<account_id>/test', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def api_test_account(account_id):
    """Test account IMAP/SMTP connectivity and update health fields."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor(); acc = cur.execute("SELECT * FROM email_accounts WHERE id=?", (account_id,)).fetchone()
    if not acc:
        conn.close(); return jsonify({'error': 'Account not found'}), 404
    imap_pwd = decrypt_credential(acc['imap_password'])
    smtp_pwd = decrypt_credential(acc['smtp_password'])
    if not acc['imap_username'] or not imap_pwd:
        conn.close(); return jsonify({'success': False, 'imap': {'success': False, 'message': 'IMAP username/password required'}, 'smtp': {'success': False, 'message': 'SMTP test skipped'}}), 400
    if not acc['smtp_username'] or not smtp_pwd:
        conn.close(); return jsonify({'success': False, 'imap': {'success': False, 'message': 'IMAP test skipped'}, 'smtp': {'success': False, 'message': 'SMTP username/password required'}}), 400
    imap_ok, imap_msg = _test_email_connection('imap', acc['imap_host'], acc['imap_port'], acc['imap_username'], imap_pwd or '', acc['imap_use_ssl'])
    smtp_ok, smtp_msg = _test_email_connection('smtp', acc['smtp_host'], acc['smtp_port'], acc['smtp_username'], smtp_pwd or '', acc['smtp_use_ssl'])
    cur.execute(
        """
        UPDATE email_accounts
        SET smtp_health_status = ?, imap_health_status = ?,
            last_health_check = CURRENT_TIMESTAMP,
            connection_status = ?
        WHERE id = ?
        """,
        (
            'connected' if smtp_ok else 'error',
            'connected' if imap_ok else 'error',
            'connected' if (smtp_ok and imap_ok) else 'error',
            account_id,
        ),
    )
    if smtp_ok and imap_ok:
        cur.execute("UPDATE email_accounts SET last_successful_connection = CURRENT_TIMESTAMP WHERE id=?", (account_id,))
    conn.commit(); conn.close()
    return jsonify({'success': smtp_ok and imap_ok, 'imap': {'success': imap_ok, 'message': imap_msg}, 'smtp': {'success': smtp_ok, 'message': smtp_msg}})


@accounts_bp.route('/api/accounts/export')
@login_required
def api_export_accounts():
    """Export non-secret account configuration as JSON file."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT account_name, email_address, provider_type,
               imap_host, imap_port, imap_username, imap_use_ssl,
               smtp_host, smtp_port, smtp_username, smtp_use_ssl
        FROM email_accounts
        ORDER BY account_name
        """
    ).fetchall(); conn.close()
    export = {'version': '1.0', 'exported_at': datetime.now().isoformat(), 'accounts': [dict(r) for r in rows]}
    resp = jsonify(export); resp.headers['Content-Disposition'] = 'attachment; filename=email_accounts_export.json'
    return resp


@accounts_bp.route('/api/test-connection/<connection_type>', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def api_test_connection(connection_type):
    """Test IMAP/SMTP connectivity to an arbitrary host using provided params."""
    data = request.get_json(silent=True) or {}
    host = data.get('host'); port = int(data.get('port')) if data.get('port') else None
    username = data.get('username'); password = data.get('password') or ''
    use_ssl = bool(data.get('use_ssl', True))
    if not (host and port and username and password):
        return jsonify({'success': False, 'message': 'Missing parameters (host, port, username, password required)', 'error': 'Missing parameters'}), 400
    ok, msg = _test_email_connection(connection_type, host, port, username, password, use_ssl)
    return jsonify({'success': ok, 'message': msg, 'error': None if ok else msg})


@accounts_bp.route('/diagnostics')
@accounts_bp.route('/diagnostics/<account_id>')
@login_required
def diagnostics(account_id=None):
    """Redirect to dashboard diagnostics tab, optionally scoped to account."""
    if account_id:
        return redirect(url_for('dashboard.dashboard', tab='diagnostics') + f'?account_id={account_id}')
    return redirect(url_for('dashboard.dashboard', tab='diagnostics'))


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

