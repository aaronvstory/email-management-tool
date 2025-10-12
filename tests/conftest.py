"""
Pytest Configuration and Fixtures for Email Management Tool
Updated for modular architecture with blueprint support and dependency injection
"""
import os
import sys
import pytest
import tempfile
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import application components using current modular structure
import simple_app as sa
from app.utils.db import get_db, DB_PATH, table_exists
from app.utils.crypto import encrypt_credential, get_encryption_key
from app.models.simple_user import SimpleUser, load_user_from_db
from simple_app import init_database

# Test configuration
os.environ['TESTING'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'test-secret-key-for-testing-only'


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing with proper configuration"""
    # Ensure encryption key exists for tests
    get_encryption_key()

    # Configure app for testing
    sa.app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    # Initialize database if needed
    if not table_exists("users"):
        init_database()

    # Create test admin user if not exists
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username='admin'")
        if not cursor.fetchone():
            from werkzeug.security import generate_password_hash
            admin_hash = generate_password_hash('admin123')
            cursor.execute(
                "INSERT INTO users(username, password_hash, role) VALUES('admin', ?, 'admin')",
                (admin_hash,)
            )
            conn.commit()

    yield sa.app


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def authenticated_client(client):
    """Create authenticated test client"""
    # Login as admin user
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)

    # Verify login was successful
    assert response.status_code == 200 or b'dashboard' in response.data.lower()

    return client


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing using dependency injection pattern"""
    # Use a separate test database for each test function
    test_db_path = tempfile.mktemp(suffix='.db')

    # Override DB_PATH for this test
    original_db_path = DB_PATH
    os.environ['DB_PATH'] = test_db_path

    try:
        # Initialize test database
        with get_db() as conn:
            init_database()

        yield get_db()

        # Cleanup test database
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)

    finally:
        # Restore original DB_PATH
        if original_db_path != DB_PATH:
            os.environ['DB_PATH'] = original_db_path


@pytest.fixture
def sample_email():
    """Create sample email message for testing"""
    return {
        'message_id': 'test-msg-001',
        'sender': 'sender@test.com',
        'recipients': ['recipient@test.com'],
        'subject': 'Test Email',
        'body_text': 'This is a test email',
        'body_html': '<p>This is a test email</p>',
        'headers': {
            'From': 'sender@test.com',
            'To': 'recipient@test.com',
            'Subject': 'Test Email',
            'Date': datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_email_with_keywords():
    """Create sample email with moderation keywords"""
    return {
        'message_id': 'test-msg-002',
        'sender': 'sender@company.com',
        'recipients': ['finance@company.com'],
        'subject': 'Urgent Invoice Payment Required',
        'body_text': 'Please process this urgent invoice for payment immediately.',
        'body_html': '<p>Please process this <b>urgent invoice</b> for payment immediately.</p>',
        'headers': {
            'From': 'sender@company.com',
            'To': 'finance@company.com',
            'Subject': 'Urgent Invoice Payment Required',
            'Date': datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_account():
    """Create sample email account for testing"""
    return {
        'account_name': 'Test Account',
        'email_address': 'test@example.com',
        'imap_host': 'imap.test.com',
        'imap_port': 993,
        'imap_username': 'test@example.com',
        'imap_password': 'test_password',
        'imap_use_ssl': True,
        'smtp_host': 'smtp.test.com',
        'smtp_port': 587,
        'smtp_username': 'test@example.com',
        'smtp_password': 'test_password',
        'smtp_use_ssl': False,
        'is_active': True
    }


@pytest.fixture
def mock_smtp_server():
    """Create mock SMTP server for testing"""
    server = MagicMock()
    server.hostname = 'localhost'
    server.port = 8587
    server.is_running = True
    return server


@pytest.fixture
def mock_imap_connection():
    """Create mock IMAP connection for testing"""
    imap = MagicMock()
    imap.select.return_value = ('OK', [b'10'])
    imap.search.return_value = ('OK', [b'1 2 3'])
    imap.fetch.return_value = ('OK', [(b'1', b'RFC822 {100}')])
    imap.login.return_value = ('OK', [])
    imap.logout.return_value = ('BYE', [])
    return imap


@pytest.fixture
def temp_config_file():
    """Create temporary configuration file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write("""
[SMTP_PROXY]
host = 0.0.0.0
port = 8587
max_message_size = 10485760

[WEB_INTERFACE]
host = 127.0.0.1
port = 5000
secret_key = test-secret-key
debug = true

[DATABASE]
database_path = :memory:

[SECURITY]
session_timeout = 30
max_login_attempts = 5
lockout_duration = 15
        """)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_email_bytes():
    """Create mock email bytes for testing"""
    email_content = b"""From: sender@test.com
To: recipient@test.com
Subject: Test Email
Date: Mon, 01 Jan 2024 12:00:00 +0000
Message-ID: <test-msg-001@test.com>
Content-Type: text/plain; charset=utf-8

This is a test email body.
"""
    return email_content


@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            import time
            self.start_time = time.time()

        def stop(self):
            import time
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any global singletons before each test"""
    # Clear any cached data that might affect tests
    # Note: No global cache found in current db module, so this is a no-op for now
    pass


@pytest.fixture
def async_loop():
    """Create async event loop for testing"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "smtp: SMTP protocol tests")
    config.addinivalue_line("markers", "imap: IMAP protocol tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "interception: Email interception tests")
    config.addinivalue_line("markers", "accounts: Account management tests")