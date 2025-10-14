"""
Pytest Configuration and Fixtures
Central configuration for all test suites
"""
import os
import sys
import pytest
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import application components
from simple_app import app as flask_app, db, User, EmailMessage
from simple_app import EmailModerationHandler, SMTPProxyServer

# Test configuration
os.environ['TESTING'] = 'True'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SMTP_PROXY_PORT'] = '8588'
os.environ['WEB_PORT'] = '5001'


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
    })
    
    with flask_app.app_context():
        db.create_all()
        
        # Create test admin user
        admin = User(
            username='admin',
            email='admin@test.com',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    
    yield flask_app
    
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def authenticated_client(client):
    """Create authenticated test client"""
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    return client


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing"""
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture
def sample_email():
    """Create sample email message"""
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
def smtp_handler():
    """Create SMTP handler for testing"""
    handler = EmailModerationHandler()
    return handler


@pytest.fixture
def mock_smtp_server():
    """Create mock SMTP server"""
    server = MagicMock()
    server.hostname = 'localhost'
    server.port = 8588
    server.is_running = True
    return server


@pytest.fixture
def mock_imap_connection():
    """Create mock IMAP connection"""
    imap = MagicMock()
    imap.select.return_value = ('OK', [b'10'])
    imap.search.return_value = ('OK', [b'1 2 3'])
    imap.fetch.return_value = ('OK', [(b'1', b'RFC822 {100}')])
    return imap


@pytest.fixture
def temp_config_file():
    """Create temporary configuration file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write("""
[SMTP_PROXY]
host = 0.0.0.0
port = 8588
max_message_size = 10485760

[SMTP_RELAY]
relay_host = smtp.test.com
relay_port = 587
use_tls = true
username = test@test.com
password = testpass

[WEB_INTERFACE]
host = 127.0.0.1
port = 5001
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
            self.start_time = datetime.now()
        
        def stop(self):
            self.end_time = datetime.now()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds()
            return None
    
    return Timer()


@pytest.fixture(autouse=True)
def reset_database(app):
    """Reset database before each test"""
    with app.app_context():
        db.session.rollback()
        
        # Clear all tables except User (keep admin)
        EmailMessage.query.delete()
        db.session.commit()


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