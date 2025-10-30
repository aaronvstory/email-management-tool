"""Simple User Model - Phase 1B Core Modularization

Extracted from simple_app.py lines 52-56
Lightweight User class for SQLite-based authentication (transitional)

NOTE: This is a simplified version for blueprint migration.
      The full SQLAlchemy models exist in user.py for future migration.
"""
from flask_login import UserMixin
import sqlite3
from app.utils.db import get_db_path


class SimpleUser(UserMixin):
    """Lightweight user model for Flask-Login authentication

    Attributes:
        id: User ID (primary key)
        username: Username for login
        role: User role (admin, moderator, user)
    """
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

    def get_role(self):
        """Get user role

        Returns:
            str: User role
        """
        return self.role

    def __repr__(self):
        return f'<SimpleUser {self.username} (role={self.role})>'


def load_user_from_db(user_id):
    """Load user from SQLite database (Flask-Login user_loader helper)

    Args:
        user_id: User ID to load

    Returns:
        SimpleUser: User object or None if not found
    """
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            columns = {row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
        except sqlite3.Error:
            columns = set()

        if 'role' in columns:
            row = cur.execute(
                "SELECT id, username, role FROM users WHERE id=?",
                (user_id,)
            ).fetchone()
            conn.close()
            if row:
                return SimpleUser(row['id'], row['username'], row['role'])
        else:
            row = cur.execute(
                "SELECT id, username FROM users WHERE id=?",
                (user_id,)
            ).fetchone()
            conn.close()
            if row:
                return SimpleUser(row['id'], row['username'], 'admin')
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
    return None
