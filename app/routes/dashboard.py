"""Dashboard Blueprint - Phase 1B Route Modularization

Extracted from simple_app.py lines 608-676
Routes: /dashboard, /dashboard/<tab>, /test-dashboard
"""
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import sqlite3
import json
from app.utils.db import DB_PATH, get_db, fetch_counts

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@dashboard_bp.route('/dashboard/<tab>')
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
        stats = fetch_counts(account_id=int(selected_account_id), include_outbound=False)

        # Get recent emails for selected account
        recent_emails = cursor.execute("""
            SELECT id, sender, recipients, subject, status, interception_status, created_at, body_text
            FROM email_messages
            WHERE account_id = ? AND (direction IS NULL OR direction!='outbound')
            ORDER BY created_at DESC
            LIMIT 20
        """, (selected_account_id,)).fetchall()
    else:
        # Get overall statistics
        stats = fetch_counts(include_outbound=False)

        # Get recent emails from all accounts
        recent_emails = cursor.execute("""
            SELECT id, sender, recipients, subject, status, interception_status, created_at, body_text
            FROM email_messages
            WHERE (direction IS NULL OR direction!='outbound')
            ORDER BY created_at DESC
            LIMIT 20
        """).fetchall()

    # Get active rules count
    active_rules = cursor.execute("SELECT COUNT(*) FROM moderation_rules WHERE is_active = 1").fetchone()[0]

    # Get all moderation rules for Rules tab
    # Check which columns exist to support both legacy and extended schemas
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(moderation_rules)").fetchall()]
    if 'rule_type' in cols and 'condition_value' in cols:
        # Extended schema
        rules = cursor.execute("""
            SELECT id, rule_name, rule_type, condition_field, condition_operator,
                   condition_value, action, priority, is_active, created_at
            FROM moderation_rules
            ORDER BY priority DESC, rule_name
        """).fetchall()
    else:
        # Legacy schema - normalize to match extended format
        rules_raw = cursor.execute("""
            SELECT id, rule_name, keyword, action, priority, is_active, created_at
            FROM moderation_rules
            ORDER BY priority DESC, rule_name
        """).fetchall()
        # Convert to dict format for template compatibility
        rules = []
        for r in rules_raw:
            rules.append({
                'id': r[0],
                'rule_name': r[1],
                'rule_type': 'KEYWORD',
                'condition_field': 'BODY',
                'condition_operator': 'CONTAINS',
                'condition_value': r[2] or '',
                'action': r[3] or 'HOLD',
                'priority': r[4] or 50,
                'is_active': r[5],
                'created_at': r[6] if len(r) > 6 else ''
            })

    # Normalize data for template
    email_payload = []
    for row in recent_emails:
        record = dict(row)
        recipients = record.get('recipients')
        if recipients:
            try:
                if isinstance(recipients, str):
                    # Attempt JSON parse, fallback to CSV
                    parsed = json.loads(recipients)
                    if isinstance(parsed, list):
                        record['recipients'] = parsed
                    else:
                        record['recipients'] = [recipients]
                else:
                    record['recipients'] = list(recipients)
            except json.JSONDecodeError:
                record['recipients'] = [addr.strip() for addr in recipients.split(',') if addr.strip()]
        else:
            record['recipients'] = []

        body = record.get('body_text') or ''
        preview = ' '.join(body.split())[:160]
        record['preview_snippet'] = preview

        email_payload.append(record)

    conn.close()

    return render_template('dashboard_unified.html',
                         stats=stats,
                         recent_emails=email_payload,
                         active_rules=active_rules,
                         rules=rules,
                         accounts=accounts,
                         selected_account_id=selected_account_id,
                         active_tab=tab,
                         pending_count=stats['pending'],
                         user=current_user)


@dashboard_bp.route('/dashboard/stitch')
@dashboard_bp.route('/dashboard/stitch/<tab>')
@login_required
def dashboard_stitch(tab='overview'):
    """Stitch design system variant of dashboard"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get email accounts
    accounts = cursor.execute("""
        SELECT id, account_name, email_address, imap_host, imap_port, smtp_host, smtp_port,
               is_active, last_checked, last_error
        FROM email_accounts
        ORDER BY account_name
    """).fetchall()

    selected_account_id = request.args.get('account_id', None)

    # Get statistics
    if selected_account_id:
        stats = fetch_counts(account_id=int(selected_account_id), include_outbound=False)
        recent_emails = cursor.execute("""
            SELECT id, sender, recipients, subject, status, interception_status, created_at, body_text
            FROM email_messages
            WHERE account_id = ? AND (direction IS NULL OR direction!='outbound')
            ORDER BY created_at DESC
            LIMIT 20
        """, (selected_account_id,)).fetchall()
    else:
        stats = fetch_counts(include_outbound=False)
        recent_emails = cursor.execute("""
            SELECT id, sender, recipients, subject, status, interception_status, created_at, body_text
            FROM email_messages
            WHERE (direction IS NULL OR direction!='outbound')
            ORDER BY created_at DESC
            LIMIT 20
        """).fetchall()

    active_rules = cursor.execute("SELECT COUNT(*) FROM moderation_rules WHERE is_active = 1").fetchone()[0]

    # Check which columns exist to support both legacy and extended schemas
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(moderation_rules)").fetchall()]
    if 'rule_type' in cols and 'condition_value' in cols:
        # Extended schema
        rules = cursor.execute("""
            SELECT id, rule_name, rule_type, condition_field, condition_operator,
                   condition_value, action, priority, is_active, created_at
            FROM moderation_rules
            ORDER BY priority DESC, rule_name
        """).fetchall()
    else:
        # Legacy schema - normalize to match extended format
        rules_raw = cursor.execute("""
            SELECT id, rule_name, keyword, action, priority, is_active, created_at
            FROM moderation_rules
            ORDER BY priority DESC, rule_name
        """).fetchall()
        # Convert to dict format for template compatibility
        rules = []
        for r in rules_raw:
            rules.append({
                'id': r[0],
                'rule_name': r[1],
                'rule_type': 'KEYWORD',
                'condition_field': 'BODY',
                'condition_operator': 'CONTAINS',
                'condition_value': r[2] or '',
                'action': r[3] or 'HOLD',
                'priority': r[4] or 50,
                'is_active': r[5],
                'created_at': r[6] if len(r) > 6 else ''
            })

    # Normalize email data
    email_payload = []
    for row in recent_emails:
        record = dict(row)
        recipients = record.get('recipients')
        if recipients:
            try:
                if isinstance(recipients, str):
                    parsed = json.loads(recipients)
                    record['recipients'] = parsed if isinstance(parsed, list) else [recipients]
                else:
                    record['recipients'] = list(recipients)
            except json.JSONDecodeError:
                record['recipients'] = [addr.strip() for addr in recipients.split(',') if addr.strip()]
        else:
            record['recipients'] = []

        body = record.get('body_text') or ''
        record['preview_snippet'] = ' '.join(body.split())[:160]
        email_payload.append(record)

    conn.close()

    return render_template('stitch/dashboard.html',
                         stats=stats,
                         recent_emails=email_payload,
                         active_rules=active_rules,
                         rules=rules,
                         accounts=accounts,
                         selected_account_id=selected_account_id,
                         active_tab=tab,
                         pending_count=stats['pending'],
                         user=current_user)


@dashboard_bp.route('/test-dashboard')
@login_required
def test_dashboard():
    """Test dashboard redirect"""
    return redirect(url_for('dashboard.dashboard'))
