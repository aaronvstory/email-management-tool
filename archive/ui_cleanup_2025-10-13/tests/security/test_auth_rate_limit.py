import re
import pytest


@pytest.fixture()
def app_client():
    import simple_app as sa
    sa.app.config['TESTING'] = True
    client = sa.app.test_client()
    return client


def _parse_hidden_csrf(html: str) -> str:
    m = re.search(r'name=[\"\']csrf_token[\"\']\s+value=[\"\']([^\"\']+)[\"\']', html, flags=re.IGNORECASE)
    return m.group(1) if m else ''


def test_protected_routes_require_authentication(app_client):
    for path in ['/emails', '/accounts', '/compose']:
        r = app_client.get(path, follow_redirects=False)
        assert r.status_code in (301, 302)
        loc = r.headers.get('Location', '')
        assert '/login' in loc


def test_login_rate_limit_triggers_429_on_6th_attempt(app_client):
    # Fetch CSRF token from login page
    ip_env = {'REMOTE_ADDR': '127.0.0.2'}
    r = app_client.get('/login', environ_overrides=ip_env)
    assert r.status_code == 200
    token = _parse_hidden_csrf(r.get_data(as_text=True))
    assert token

    # 5 failed attempts should be allowed (not 429)
    for _ in range(5):
        r_bad = app_client.post(
            '/login',
            json={'username': 'admin', 'password': 'wrong'},
            headers={'X-CSRFToken': token},
            environ_overrides=ip_env,
        )
        assert r_bad.status_code in (200, 400)

    # 6th attempt should trigger rate limit with JSON 429
    r_limit = app_client.post(
        '/login',
        json={'username': 'admin', 'password': 'wrong'},
        headers={'X-CSRFToken': token},
        environ_overrides=ip_env,
    )
    assert r_limit.status_code == 429
    # Body should indicate rate limit error
    data = r_limit.get_json()
    assert isinstance(data, dict) and 'error' in data


def test_authenticated_access_to_protected_routes(app_client):
    # Login with valid credentials using form + csrf
    ip_env = {'REMOTE_ADDR': '127.0.0.3'}
    r = app_client.get('/login', environ_overrides=ip_env)
    token = _parse_hidden_csrf(r.get_data(as_text=True))
    assert token
    r2 = app_client.post('/login', data={'username': 'admin', 'password': 'admin123', 'csrf_token': token}, follow_redirects=False, environ_overrides=ip_env)
    assert r2.status_code in (301, 302)

    # Now protected pages should be accessible
    r_emails = app_client.get('/emails', follow_redirects=False, environ_overrides=ip_env)
    assert r_emails.status_code == 200
    r_accounts = app_client.get('/accounts', follow_redirects=False, environ_overrides=ip_env)
    assert r_accounts.status_code == 200
    r_compose = app_client.get('/compose', follow_redirects=False, environ_overrides=ip_env)
    assert r_compose.status_code == 200
