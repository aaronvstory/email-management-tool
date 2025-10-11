import os
import re
import sqlite3
import tempfile
import pytest
from pathlib import Path


@pytest.fixture(scope='session', autouse=True)
def _setup_test_env():
    # Ensure strong secret for import-time checks
    os.environ.setdefault('FLASK_SECRET_KEY', '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef')
    yield


# Per-test DB isolation - creates isolated test database for each test
@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Provide an isolated test database for each test."""
    test_db = tmp_path / 'test_email_manager.db'
    monkeypatch.setenv('TEST_DB_PATH', str(test_db))

    # Initialize schema
    try:
        from simple_app import init_database
        import simple_app
        # Temporarily override DB_PATH
        original_db = simple_app.DB_PATH
        simple_app.DB_PATH = str(test_db)
        init_database()
        simple_app.DB_PATH = original_db
    except Exception as e:
        pytest.fail(f"Failed to initialize test database: {e}")

    yield str(test_db)

    # Cleanup
    try:
        if test_db.exists():
            test_db.unlink()
    except Exception:
        pass


# Per-test DB isolation for latency stats tests (they assume isolated DB per test)
@pytest.fixture(autouse=True)
def _isolate_db_for_latency_tests(request, tmp_path):
    fspath = getattr(request.node, 'fspath', None)
    if fspath and 'test_latency_stats.py' in str(fspath):
        prev = os.environ.get('TEST_DB_PATH')
        test_db = tmp_path / 'latency_test.db'
        os.environ['TEST_DB_PATH'] = str(test_db)
        # Initialize schema for this fresh DB
        try:
            from simple_app import init_database
            init_database()
        except Exception:
            pass
        # Reset latency cache to avoid cross-test contamination
        try:
            import importlib
            stats_mod = importlib.import_module('app.routes.stats')
            if hasattr(stats_mod, '_LAT_CACHE'):
                stats_mod._LAT_CACHE['t'] = 0.0
                stats_mod._LAT_CACHE['v'] = None
        except Exception:
            pass
        try:
            yield
        finally:
            # Restore previous TEST_DB_PATH after test
            if prev is not None:
                os.environ['TEST_DB_PATH'] = prev
            else:
                os.environ.pop('TEST_DB_PATH', None)
        return
    yield


def _parse_hidden_csrf(html: str) -> str:
    m = re.search(r'name=[\"\']csrf_token[\"\']\s+value=[\"\']([^\"\']+)[\"\']', html, flags=re.IGNORECASE)
    return m.group(1) if m else ''


@pytest.fixture()
def app():
    """Provide Flask app instance for pytest-flask compatibility."""
    import simple_app as sa
    sa.app.config['TESTING'] = True
    sa.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
    return sa.app


@pytest.fixture()
def app_client(app):
    """Provide test client with TESTING enabled."""
    return app.test_client()


@pytest.fixture()
def authenticated_client(app_client):
    """Provide authenticated test client with valid session."""
    r = app_client.get('/login')
    html = r.get_data(as_text=True)
    token = _parse_hidden_csrf(html)

    if not token:
        # If CSRF is disabled, try without token
        r = app_client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)
    else:
        r = app_client.post('/login', data={'username': 'admin', 'password': 'admin123', 'csrf_token': token}, follow_redirects=False)

    return app_client


@pytest.fixture()
def db_session(isolated_db):
    """Provide database session with isolated test database."""
    conn = sqlite3.connect(isolated_db)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture()
def session(db_session):
    """Alias for db_session to match test expectations."""
    return db_session


@pytest.fixture()
def client(app):
    """Alias for app.test_client() to match pytest-flask expectations."""
    return app.test_client()


# Register custom pytest marks
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "smtp: mark test as requiring SMTP")
    config.addinivalue_line("markers", "imap: mark test as requiring IMAP")