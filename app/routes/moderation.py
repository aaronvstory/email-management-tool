"""Moderation Rules Blueprint - Phase 1B Route Modularization

Extracted from simple_app.py lines 859-875
Routes: /rules
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
import sqlite3
from app.utils.db import DB_PATH

moderation_bp = Blueprint('moderation', __name__)


@moderation_bp.route('/rules')
@login_required
def rules():
    """Moderation rules page"""
    if current_user.role != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard.dashboard'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rules = cursor.execute("SELECT * FROM moderation_rules ORDER BY priority DESC").fetchall()

    conn.close()

    return render_template('rules.html', rules=rules)
