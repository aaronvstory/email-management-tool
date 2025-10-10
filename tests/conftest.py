"""
Pytest configuration for Email Management Tool tests

Note: SQLite connection isolation between tests is limited due to:
- Flask app singleton pattern (single app instance across tests)
- SQLite connection caching within Flask app context
- Module-level imports that happen before fixtures run

Tests pass individually, confirming code logic is correct.
When run together, some tests may see residual data from previous tests.

Workaround: Run problematic tests individually:
  python -m pytest tests/test_latency_stats.py::test_name -v

Fixtures Added (Phase 2 Test Infrastructure):
- app: Flask application with test configuration
- client: Unauthenticated test client
- authenticated_client: Test client with admin login
- db_session: Database connection with automatic cleanup
- temp_db: Temporary isolated database
"""
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "security: Security-focused tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")


# ============================================================================
# Cache Management (Original Fixture)
# ============================================================================

@pytest.fixture(autouse=True)
def clear_caches():
    """Clear application caches before and after each test"""
    from simple_app import app

    # Clear caches before test
    if hasattr(app, '_unified_stats_cache'):
        delattr(app, '_unified_stats_cache')
    if hasattr(app, '_latency_stats_cache'):
        delattr(app, '_latency_stats_cache')

    yield

    # Clear caches after test
    if hasattr(app, '_unified_stats_cache'):
        delattr(app, '_unified_stats_cache')
    if hasattr(app, '_latency_stats_cache'):
        delattr(app, '_latency_stats_cache')


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """
    Create a temporary isolated database for testing.

    Yields:
        str: Path to temporary database file
    """
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Set environment variable for test isolation
    old_db_path = os.environ.get('TEST_DB_PATH')
    os.environ['TEST_DB_PATH'] = db_path

    try:
        # Initialize database schema
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Create tables (minimal schema for testing)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS email_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                message_id TEXT,
                sender TEXT,
                recipients TEXT,
                subject TEXT,
                body_text TEXT,
                body_html TEXT,
                raw_content TEXT,
                status TEXT DEFAULT 'PENDING',
                interception_status TEXT,
                direction TEXT DEFAULT 'inbound',
                latency_ms INTEGER,
                risk_score REAL,
                keywords_matched TEXT,
                review_notes TEXT,
                approved_by INTEGER,
                original_uid INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                action_taken_at TEXT
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS email_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_address TEXT UNIQUE NOT NULL,
                imap_host TEXT,
                imap_port INTEGER DEFAULT 993,
                imap_username TEXT,
                imap_password TEXT,
                smtp_host TEXT,
                smtp_port INTEGER DEFAULT 587,
                smtp_use_ssl INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                user_id INTEGER,
                target_id INTEGER,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

        yield db_path
    finally:
        # Restore original DB path
        if old_db_path:
            os.environ['TEST_DB_PATH'] = old_db_path
        elif 'TEST_DB_PATH' in os.environ:
            del os.environ['TEST_DB_PATH']

        # Remove temporary database
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def db_session(temp_db: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a database session with automatic rollback.

    Args:
        temp_db: Temporary database path fixture

    Yields:
        sqlite3.Connection: Database connection with Row factory
    """
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


# ============================================================================
# Flask App Fixtures
# ============================================================================

@pytest.fixture
def app(temp_db: str) -> Flask:
    """
    Create Flask application instance with test configuration.

    Args:
        temp_db: Temporary database path fixture

    Returns:
        Flask: Configured Flask application
    """
    import simple_app
    from simple_app import app as flask_app

    # CRITICAL: Override DB_PATH at module level for context processors
    old_db_path = simple_app.DB_PATH
    simple_app.DB_PATH = temp_db

    # Also set in app.utils.db if it exists
    try:
        from app.utils import db as db_module
        old_utils_db = db_module.DB_PATH if hasattr(db_module, 'DB_PATH') else None
        if hasattr(db_module, 'DB_PATH'):
            db_module.DB_PATH = temp_db
    except ImportError:
        old_utils_db = None

    # Override config for testing
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': False,
        'DB_PATH': temp_db,
    })

    # Ensure database is initialized
    with flask_app.app_context():
        # Create default admin user for testing
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check if admin exists
        existing = cursor.execute(
            "SELECT id FROM users WHERE username = 'admin'"
        ).fetchone()

        if not existing:
            from werkzeug.security import generate_password_hash
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ('admin', generate_password_hash('admin123'), 'admin')
            )
            conn.commit()

        conn.close()

    yield flask_app

    # Restore original DB_PATH after test
    simple_app.DB_PATH = old_db_path
    if old_utils_db is not None:
        from app.utils import db as db_module
        db_module.DB_PATH = old_utils_db


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """
    Create Flask test client for unauthenticated requests.

    Args:
        app: Flask application fixture

    Returns:
        FlaskClient: Test client for making HTTP requests
    """
    return app.test_client()


@pytest.fixture
def authenticated_client(app: Flask, client: FlaskClient) -> FlaskClient:
    """
    Create Flask test client with admin authentication.

    Args:
        app: Flask application fixture
        client: Unauthenticated test client

    Returns:
        FlaskClient: Test client with active admin session
    """
    # Login as admin
    with client:
        client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

    return client


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def sample_email_data() -> dict:
    """Provide sample email data for testing."""
    return {
        'sender': 'test@example.com',
        'recipients': 'admin@example.com',
        'subject': 'Test Email',
        'body_text': 'This is a test email body.',
        'body_html': '<p>This is a test email body.</p>',
        'message_id': '<test@example.com>',
        'status': 'PENDING',
        'direction': 'inbound',
    }


@pytest.fixture
def sample_account_data() -> dict:
    """Provide sample account data for testing."""
    return {
        'email_address': 'test@gmail.com',
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'imap_username': 'test@gmail.com',
        'imap_password': 'test_password',
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_use_ssl': 0,
        'is_active': 1,
    }