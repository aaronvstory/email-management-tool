"""
Test for /api/unified-stats endpoint
Verifies unified statistics combining legacy and interception statuses
"""
import pytest


def test_unified_stats_endpoint():
    """Test unified stats endpoint returns correct data structure"""
    from simple_app import app
    client = app.test_client()

    # Login first (required for @login_required)
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'  # Mock user ID

    r = client.get('/api/unified-stats')
    assert r.status_code == 200

    data = r.get_json()

    # Basic shape verification
    for k in ('total', 'pending', 'held', 'released'):
        assert k in data, f"Missing key: {k}"
        assert isinstance(data[k], int), f"Key {k} should be integer"

    # Totals consistency check
    assert data['total'] >= 0
    assert data['pending'] >= 0
    assert data['held'] >= 0
    assert data['released'] >= 0


def test_unified_stats_cache():
    """Test that unified stats uses 5s cache"""
    from simple_app import app
    import time

    client = app.test_client()

    # Mock session
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'

    # First request
    r1 = client.get('/api/unified-stats')
    data1 = r1.get_json()

    # Immediate second request should use cache
    r2 = client.get('/api/unified-stats')
    data2 = r2.get_json()

    assert data1 == data2, "Cached response should be identical"

    # Wait 6 seconds and request again (cache should expire)
    time.sleep(6)
    r3 = client.get('/api/unified-stats')
    data3 = r3.get_json()

    # Structure should still be valid
    assert 'total' in data3
    assert 'pending' in data3
    assert 'held' in data3
    assert 'released' in data3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])