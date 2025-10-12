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
from app.extensions import limiter, csrf
import csv
from io import StringIO

# Phase 3: Import consolidated email helpers
from app.utils.email_helpers import detect_email_settings as _detect_email_settings, test_email_connection as _test_email_connection

accounts_bp = Blueprint('accounts', __name__)

# Safe int conversion helper
_def = object()

def _to_int(val, default=None):
    try:
        return int(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


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


@accounts_bp.route('/api/accounts/bulk-delete', methods=['POST'])
@csrf.exempt
@login_required
def api_accounts_bulk_delete():
    """Bulk delete email accounts by ids.
    Body: {"ids": [1,2,3]}
    """
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    data = request.get_json(silent=True) or {}
    ids = data.get('ids') or []
    if not isinstance(ids, list) or not ids:
        return jsonify({'success': False, 'error': 'No ids provided'}), 400
    # Normalize to ints and filter invalid
    try:
        id_list = [int(i) for i in ids if str(i).isdigit()]
    except Exception:
        id_list = []
    if not id_list:
        return jsonify({'success': False, 'error': 'No valid ids provided'}), 400
    # Best-effort: stop watchers and clear heartbeats first
    try:
        from simple_app import stop_imap_watcher_for_account
        for aid in id_list:
            try:
                stop_imap_watcher_for_account(aid)
            except Exception:
                pass
    except Exception:
        pass
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        # Remove heartbeats for these accounts
        try:
            cur.executemany("DELETE FROM worker_heartbeats WHERE worker_id=?", [(f"imap_{aid}",) for aid in id_list])
        except Exception:
            pass
        # Delete accounts
        qmarks = ",".join(["?"] * len(id_list))
        cur.execute(f"DELETE FROM email_accounts WHERE id IN ({qmarks})", id_list)
        conn.commit()
        deleted = cur.rowcount if cur.rowcount is not None else len(id_list)
    finally:
        conn.close()
    return jsonify({'success': True, 'deleted': deleted, 'ids': id_list})


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
    imap_ok, imap_msg = _test_email_connection('imap', str(acc['imap_host'] or ''), _to_int(acc['imap_port'], 993), str(acc['imap_username'] or ''), imap_pwd or '', bool(acc['imap_use_ssl']))
    smtp_ok, smtp_msg = _test_email_connection('smtp', str(acc['smtp_host'] or ''), _to_int(acc['smtp_port'], 465), str(acc['smtp_username'] or ''), smtp_pwd or '', bool(acc['smtp_use_ssl']))
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
    host = str(data.get('host') or '').strip(); port = _to_int(data.get('port'), None)
    username = str(data.get('username') or '').strip(); password = str(data.get('password') or '')
    use_ssl = bool(data.get('use_ssl', True))
    if not (host and port and username and password):
        return jsonify({'success': False, 'message': 'Missing parameters (host, port, username, password required)', 'error': 'Missing parameters'}), 400
    ok, msg = _test_email_connection(connection_type, host, int(port), username, password, use_ssl)
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
    base_templates = getattr(current_app, 'template_folder', None) or os.path.join(current_app.root_path, 'templates')
    template_path = os.path.join(base_templates, 'accounts_simple.html')
    if os.path.exists(template_path):
        return render_template('accounts_simple.html', accounts=accounts)
    else:
        accounts_dict = {acc['id']: dict(acc) for acc in accounts}
        return render_template('accounts.html', accounts=accounts_dict)


@accounts_bp.route('/accounts/import', methods=['GET'])
@login_required
def accounts_import_page():
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard.dashboard'))
    return render_template('accounts_import.html')


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
            imap_port = _to_int(request.form.get('imap_port'), 993)
            imap_username = request.form.get('imap_username')
            imap_password = request.form.get('imap_password')
            imap_use_ssl = request.form.get('imap_use_ssl') == 'on'

            smtp_host = request.form.get('smtp_host')
            smtp_port = _to_int(request.form.get('smtp_port'), 465)
            smtp_username = request.form.get('smtp_username')
            smtp_password = request.form.get('smtp_password')
            smtp_use_ssl = request.form.get('smtp_use_ssl') == 'on'

        imap_ok, imap_msg = _test_email_connection('imap', str(imap_host or ''), _to_int(imap_port, 993), str(imap_username or ''), imap_password or '', bool(imap_use_ssl))
        smtp_ok, smtp_msg = _test_email_connection('smtp', str(smtp_host or ''), _to_int(smtp_port, 465), str(smtp_username or ''), smtp_password or '', bool(smtp_use_ssl))

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

        # Validate account_id is not None (shouldn't happen for successful INSERT)
        if account_id is None:
            flash('Failed to create account: database error', 'error')
            return redirect(url_for('accounts.email_accounts'))

        # Try to start IMAP watcher for the new account (best effort)
        try:
            from simple_app import monitor_imap_account, imap_threads  # lazy import to avoid circular at import time
            import threading
            thread = threading.Thread(target=monitor_imap_account, args=(account_id,), daemon=True)
            imap_threads[account_id] = thread  # account_id is now guaranteed to be int
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


@accounts_bp.route('/api/accounts/import', methods=['POST'])
@csrf.exempt
@login_required
def api_import_accounts():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    file = request.files.get('file')
    auto_detect = (request.form.get('auto_detect') == 'on') or (request.args.get('auto_detect') == '1')
    if not file:
        return jsonify({'success': False, 'error': 'CSV file is required'}), 400
    try:
        content = file.read().decode('utf-8', errors='ignore')
        reader = csv.DictReader(StringIO(content))
        rows = list(reader)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Invalid CSV: {e}'}), 400

    inserted = updated = errors = 0
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        for row in rows:
            try:
                # Normalize
                r = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                email = r.get('email_address') or r.get('email')
                if not email:
                    raise ValueError('email_address missing')
                account_name = r.get('account_name') or email
                imap_user = r.get('imap_username') or email
                smtp_user = r.get('smtp_username') or email
                imap_pwd = r.get('imap_password')
                smtp_pwd = r.get('smtp_password')
                if not imap_pwd or not smtp_pwd:
                    raise ValueError('imap_password and smtp_password required')
                def _to_int(v, d=None):
                    try: return int(v)
                    except Exception: return d
                def _to_bool(v, d=None):
                    if v is None: return d
                    s = str(v).strip().lower()
                    if s in ('1','true','yes','y'): return True
                    if s in ('0','false','no','n'): return False
                    return d
                imap_host = r.get('imap_host'); smtp_host = r.get('smtp_host')
                imap_port = _to_int(r.get('imap_port'), 993); smtp_port = _to_int(r.get('smtp_port'), 465)
                imap_ssl = _to_bool(r.get('imap_use_ssl'), True); smtp_ssl = _to_bool(r.get('smtp_use_ssl'), True)
                if auto_detect and (not imap_host or not smtp_host):
                    auto = _detect_email_settings(email)
                    imap_host = imap_host or auto['imap_host']
                    imap_port = imap_port or auto['imap_port']
                    imap_ssl = auto['imap_use_ssl'] if imap_ssl is None else imap_ssl
                    smtp_host = smtp_host or auto['smtp_host']
                    smtp_port = smtp_port or auto['smtp_port']
                    smtp_ssl = auto['smtp_use_ssl'] if smtp_ssl is None else smtp_ssl
                is_active = 1 if _to_bool(r.get('is_active'), True) else 0

                enc_imap = encrypt_credential(imap_pwd)
                enc_smtp = encrypt_credential(smtp_pwd)
                existing = cur.execute("SELECT id FROM email_accounts WHERE email_address=?", (email,)).fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE email_accounts
                        SET account_name=?,
                            imap_host=?, imap_port=?, imap_username=?, imap_password=?, imap_use_ssl=?,
                            smtp_host=?, smtp_port=?, smtp_username=?, smtp_password=?, smtp_use_ssl=?,
                            is_active=?, updated_at=CURRENT_TIMESTAMP
                        WHERE email_address=?
                        """,
                        (
                            account_name,
                            imap_host, imap_port, imap_user, enc_imap, 1 if (imap_ssl is not False) else 0,
                            smtp_host, smtp_port, smtp_user, enc_smtp, 1 if (smtp_ssl is not False) else 0,
                            is_active, email
                        )
                    ); updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO email_accounts (
                            account_name, email_address,
                            imap_host, imap_port, imap_username, imap_password, imap_use_ssl,
                            smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_ssl,
                            is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            account_name, email,
                            imap_host, imap_port, imap_user, enc_imap, 1 if (imap_ssl is not False) else 0,
                            smtp_host, smtp_port, smtp_user, enc_smtp, 1 if (smtp_ssl is not False) else 0,
                            is_active
                        )
                    ); inserted += 1
            except Exception as e:
                errors += 1
                current_app.logger.warning(f"Import row error for {row.get('email_address')}: {e}")
        conn.commit()
    finally:
        conn.close()
    return jsonify({'success': True, 'inserted': inserted, 'updated': updated, 'errors': errors})

@accounts_bp.route('/api/accounts/<int:account_id>/monitor/start', methods=['POST'])
@csrf.exempt
@login_required
def api_start_monitor(account_id: int):
    """Activate and start IMAP monitoring for a specific account."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    # Validate credentials present
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    acc = cur.execute("SELECT * FROM email_accounts WHERE id=?", (account_id,)).fetchone()
    if not acc:
        conn.close(); return jsonify({'success': False, 'error': 'Account not found'}), 404
    imap_user = acc['imap_username'] or acc['email_address']
    imap_pwd = decrypt_credential(acc['imap_password']) if acc['imap_password'] else None
    if not imap_user or not imap_pwd:
        conn.close(); return jsonify({'success': False, 'error': 'IMAP credentials missing'}), 400
    # Set active and start watcher via simple_app helper
    cur.execute("UPDATE email_accounts SET is_active=1 WHERE id=?", (account_id,)); conn.commit(); conn.close()
    try:
        from simple_app import start_imap_watcher_for_account
        ok = start_imap_watcher_for_account(account_id)
    except Exception as e:
        ok = False
    return jsonify({'success': bool(ok)})

@accounts_bp.route('/api/accounts/<int:account_id>/monitor/stop', methods=['POST'])
@csrf.exempt
@login_required
def api_stop_monitor(account_id: int):
    """Deactivate and stop IMAP monitoring for a specific account."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    # Deactivate and signal stop
    try:
        from simple_app import stop_imap_watcher_for_account
        stop_imap_watcher_for_account(account_id)
    except Exception:
        pass
    # Confirm deactivation
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE email_accounts SET is_active=0 WHERE id=?", (account_id,)); conn.commit(); conn.close()
    return jsonify({'success': True})

@accounts_bp.route('/api/accounts/<int:account_id>/monitor/restart', methods=['POST'])
@csrf.exempt
@login_required
def api_restart_monitor(account_id: int):
    """Quick restart for an IMAP watcher: stop then start (best-effort)."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    try:
        from simple_app import stop_imap_watcher_for_account, start_imap_watcher_for_account
        stop_imap_watcher_for_account(account_id)
        ok = start_imap_watcher_for_account(account_id)
        return jsonify({'success': bool(ok)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@accounts_bp.route('/api/watchers/status')
@login_required
def api_watchers_status():
    """Return recent IMAP watcher heartbeats for UI badges/diagnostics."""
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        # Ensure column existence detection for error_count
        cols = [r[1] for r in cur.execute("PRAGMA table_info(worker_heartbeats)").fetchall()]
        has_err = 'error_count' in cols
        query = (
            "SELECT worker_id, last_heartbeat, status" + (", error_count" if has_err else "") +
            " FROM worker_heartbeats WHERE datetime(last_heartbeat) > datetime('now','-2 minutes') ORDER BY last_heartbeat DESC"
        )
        rows = cur.execute(query).fetchall()
        payload = [dict(r) for r in rows]
    except Exception:
        payload = []
    finally:
        conn.close()
    return jsonify({'success': True, 'workers': payload})

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