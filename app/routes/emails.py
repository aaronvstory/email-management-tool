"""Email Management Blueprint - Phase 1B Route Modularization

Extracted from simple_app.py lines 721-2197
Routes: /emails, /email/<id>, /email/<id>/action, /inbox, /compose, /api/held, /api/emails/pending
Plus API routes for reply/forward, download, intercept
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
import sqlite3
import os
import json
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.utils.db import DB_PATH, get_db, fetch_counts
from app.utils.crypto import decrypt_credential
from app.services.audit import log_action

emails_bp = Blueprint('emails', __name__)

@emails_bp.route('/emails')
@login_required
def email_queue():
    status_filter = request.args.get('status', 'PENDING')
    account_id = request.args.get('account_id', type=int)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    accounts = cursor.execute(
        """
        SELECT id, account_name, email_address
        FROM email_accounts
        WHERE is_active = 1
        ORDER BY account_name
        """
    ).fetchall()

    counts = fetch_counts(account_id=int(account_id) if account_id else None)
    pending_count = counts.get('pending', 0)
    approved_count = counts.get('approved', 0)
    rejected_count = counts.get('rejected', 0)
    total_count = counts.get('total', 0)

    if account_id:
        if status_filter.upper() == 'ALL':
            emails = cursor.execute(
                """
                SELECT * FROM email_messages
                WHERE account_id = ?
                ORDER BY created_at DESC
                """,
                (account_id,),
            ).fetchall()
        else:
            emails = cursor.execute(
                """
                SELECT * FROM email_messages
                WHERE status = ? AND account_id = ?
                ORDER BY created_at DESC
                """,
                (status_filter, account_id),
            ).fetchall()
    else:
        if status_filter.upper() == 'ALL':
            emails = cursor.execute(
                """
                SELECT * FROM email_messages
                ORDER BY created_at DESC
                """
            ).fetchall()
        else:
            emails = cursor.execute(
                """
                SELECT * FROM email_messages
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status_filter,),
            ).fetchall()

    conn.close()

    return render_template(
        'email_queue.html',
        emails=emails,
        current_filter=status_filter,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        total_count=total_count,
        accounts=accounts,
        selected_account_id=str(account_id) if account_id else None,
    )


@emails_bp.route('/email/<int:email_id>')
@login_required
def view_email(email_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    email_row = cursor.execute("SELECT * FROM email_messages WHERE id = ?", (email_id,)).fetchone()

    if not email_row:
        conn.close()
        flash('Email not found', 'error')
        return redirect(url_for('emails.email_queue'))

    conn.close()

    email_data = dict(email_row)
    try:
        email_data['recipients'] = json.loads(email_data['recipients']) if email_data['recipients'] else []
    except (json.JSONDecodeError, TypeError):
        if isinstance(email_data['recipients'], str):
            email_data['recipients'] = [r.strip() for r in email_data['recipients'].split(',') if r.strip()]
        else:
            email_data['recipients'] = []

    try:
        email_data['keywords_matched'] = json.loads(email_data['keywords_matched']) if email_data['keywords_matched'] else []
    except (json.JSONDecodeError, TypeError):
        if isinstance(email_data['keywords_matched'], str):
            email_data['keywords_matched'] = [k.strip() for k in email_data['keywords_matched'].split(',') if k.strip()]
        else:
            email_data['keywords_matched'] = []

    return render_template('email_viewer.html', email=email_data)


@emails_bp.route('/email/<int:email_id>/action', methods=['POST'])
@login_required
def email_action(email_id):
    action = request.form.get('action', '').upper()
    notes = request.form.get('notes', '')

    if action not in ['APPROVE', 'REJECT']:
        return jsonify({'error': 'Invalid action'}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    new_status = 'APPROVED' if action == 'APPROVE' else 'REJECTED'
    # Detect optional reviewed_at column for backward compatibility
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(email_messages)").fetchall()]
    if 'reviewed_at' in cols:
        cursor.execute(
            """
            UPDATE email_messages
            SET status = ?, reviewer_id = ?, review_notes = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_status, current_user.id, notes, email_id),
        )
    else:
        cursor.execute(
            """
            UPDATE email_messages
            SET status = ?, reviewer_id = ?, review_notes = ?
            WHERE id = ?
            """,
            (new_status, current_user.id, notes, email_id),
        )

    log_action(action, current_user.id, email_id, f"Email {action.lower()}d with notes: {notes}")

    conn.commit()
    conn.close()

    flash(f'Email {action.lower()}d successfully', 'success')
    return redirect(url_for('emails.email_queue'))
