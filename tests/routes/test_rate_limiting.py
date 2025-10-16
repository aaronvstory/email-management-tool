"""Tests for API rate limiting behaviour."""

import sqlite3


def test_edit_endpoint_rate_limit_exceeded(client, test_db_path):
    """Ensure 31st request within window returns HTTP 429."""
    # Insert HELD message required by endpoint
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        """
        INSERT INTO email_messages (id, subject, interception_status, status)
        VALUES (1, 'Initial Subject', 'HELD', 'PENDING')
        """
    )
    conn.commit()
    conn.close()

    # Login without triggering dashboard queries that require extended schema
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)

    client.environ_base['REMOTE_ADDR'] = '203.0.113.10'

    # First 30 requests should succeed (update subject each time)
    for i in range(30):
        resp = client.post(
            '/api/email/1/edit',
            json={'subject': f'Updated Subject {i}'}
        )
        assert resp.status_code == 200

    # 31st request expected to be rate limited
    blocked = client.post(
        '/api/email/1/edit',
        json={'subject': 'Rate Limited'}
    )

    assert blocked.status_code == 429
    payload = blocked.get_json()
    assert payload.get('error') == 'Rate limit exceeded'
    assert 'retry_after' in payload
    assert blocked.headers.get('Retry-After') is not None
