"""
Diagnostics & Test Utilities Blueprint
Routes moved from simple_app.py to keep the entrypoint thin.
"""
import os
import json
import sqlite3
import time
import smtplib
from datetime import datetime
from email.utils import formatdate, make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.utils.db import DB_PATH
import os

diagnostics_bp = Blueprint('diagnostics', __name__)


@diagnostics_bp.route('/test/cross-account', methods=['POST'])
@login_required
def run_cross_account_test():
    try:
        import subprocess
        result = subprocess.run(['python', 'cross_account_test.py'], capture_output=True, text=True, timeout=60)
        output = result.stdout
        success = "TEST PASSED" in output
        return jsonify({'success': success, 'output': output, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@diagnostics_bp.route('/api/test-status')
@login_required
def get_test_status():
    try:
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


@diagnostics_bp.route('/diagnostics/test', methods=['POST'])
@login_required
def test_email_send():
    flash('Email diagnostics send test temporarily disabled (module deprecated).', 'warning')
    return redirect(url_for('accounts.diagnostics'))


@diagnostics_bp.route('/interception-test')
@login_required
def interception_test_dashboard():
    return render_template('interception_test_dashboard.html', timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@diagnostics_bp.route('/api/test/send-email', methods=['POST'])
@login_required
def api_test_send_email():
    data = request.get_json(silent=True) or {}
    from_account_id = data.get('from_account_id'); to_account_id = data.get('to_account_id')
    subject = data.get('subject') or 'Test'; body = data.get('body') or 'Test body'
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
        smtp_host = os.environ.get('SMTP_PROXY_HOST', '127.0.0.1')
        smtp_port = int(os.environ.get('SMTP_PROXY_PORT', '8587'))
        smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=5); smtp.send_message(msg); smtp.quit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@diagnostics_bp.route('/api/test/check-interception')
@login_required
def api_test_check_interception():
    try:
        subject = request.args.get('subject')
        conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        email = cursor.execute(
            """
            SELECT id, subject, status, created_at
            FROM email_messages
            WHERE subject = ? AND status = 'PENDING'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (subject,),
        ).fetchone(); conn.close()
        if email:
            return jsonify({'success': True, 'email_id': email['id'], 'subject': email['subject'], 'status': email['status']})
        return jsonify({'success': False, 'message': 'Email not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@diagnostics_bp.route('/api/test/verify-delivery', methods=['POST'])
@login_required
def api_test_verify_delivery():
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
