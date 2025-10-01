"""Database utilities for Email Management Tool"""
import sqlite3
import os

def get_db_path():
    """Get the current database path (supports test isolation)"""
    return os.environ.get('TEST_DB_PATH', "email_manager.db")

def get_db():
    """Get database connection with Row factory for dict-like access"""
    conn = sqlite3.connect(get_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

# Module-level __getattr__ for dynamic DB_PATH resolution
def __getattr__(name):
    if name == 'DB_PATH':
        return get_db_path()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def table_exists(name: str) -> bool:
    """Check if table exists in database"""
    with get_db() as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None

def get_all_messages(status_filter=None, limit=200):
    """
    Unified accessor: returns rows considering both legacy status and new interception_status.
    status_filter can be 'PENDING','HELD','RELEASED', etc.
    """
    conn = get_db()
    cur = conn.cursor()
    if status_filter == 'HELD':
        return cur.execute("""
            SELECT * FROM email_messages
            WHERE interception_status='HELD'
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    if status_filter == 'RELEASED':
        return cur.execute("""
            SELECT * FROM email_messages
            WHERE interception_status='RELEASED' OR status IN ('SENT','APPROVED','DELIVERED')
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    if status_filter:
        return cur.execute("""
            SELECT * FROM email_messages
            WHERE status=?
            ORDER BY id DESC LIMIT ?
        """, (status_filter, limit)).fetchall()
    return cur.execute("""
        SELECT * FROM email_messages
        ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()