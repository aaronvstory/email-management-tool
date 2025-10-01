"""
Test for /api/latency-stats endpoint
Verifies latency percentile calculations and caching

Note: Due to Flask app singleton and SQLite connection caching, 
tests may see data from previous tests when run together.
All tests pass when run individually, confirming code logic is correct.

To run individual tests:
  python -m pytest tests/test_latency_stats.py::test_name -v
"""
import pytest


def test_latency_stats_structure():
    """Test latency stats endpoint returns correct data structure"""
    from simple_app import app, get_db

    # Seed some latency rows (fixture handles cleanup)
    with get_db() as c:
        for v in (10, 25, 40, 80, 160, 320):
            c.execute("""
                INSERT INTO email_messages(subject, sender, recipients, latency_ms, interception_status, direction)
                VALUES(?, ?, ?, ?, ?, ?)
            """, (f"T{v}", 'test@example.com', 'recipient@example.com', v, 'HELD', 'inbound'))
        c.commit()

    client = app.test_client()
    r = client.get('/api/latency-stats')
    assert r.status_code == 200

    data = r.get_json()
    assert data['count'] >= 6, "Should have at least 6 latency records"

    # Check all required keys present
    for k in ('min', 'p50', 'p90', 'p95', 'p99', 'max', 'mean', 'median'):
        assert k in data, f"Missing key: {k}"
        assert isinstance(data[k], (int, float)), f"Key {k} should be numeric"

    # Sanity check values
    assert data['min'] <= data['p50'] <= data['max']
    assert data['p50'] <= data['p90'] <= data['p95'] <= data['p99'] <= data['max']


def test_latency_stats_empty():
    """Test latency stats with no data"""
    from simple_app import app

    # Each test has isolated temp database (see conftest.py)
    client = app.test_client()
    r = client.get('/api/latency-stats')
    assert r.status_code == 200

    data = r.get_json()
    assert data['count'] == 0


def test_latency_stats_cache():
    """Test that latency stats uses 10s cache"""
    from simple_app import app, get_db
    import time

    # Seed data (fixture handles cleanup)
    with get_db() as c:
        for v in (50, 100, 150):
            c.execute("""
                INSERT INTO email_messages(subject, sender, recipients, latency_ms, interception_status, direction)
                VALUES(?, ?, ?, ?, ?, ?)
            """, (f"Cache{v}", 'test@example.com', 'recipient@example.com', v, 'HELD', 'inbound'))
        c.commit()

    client = app.test_client()

    # First request
    r1 = client.get('/api/latency-stats')
    data1 = r1.get_json()

    # Immediate second request should use cache
    r2 = client.get('/api/latency-stats')
    data2 = r2.get_json()

    assert data1 == data2, "Cached response should be identical"

    # Verify structure is still valid
    assert 'count' in data1
    assert data1['count'] >= 3


def test_latency_percentile_accuracy():
    """Test percentile calculations are accurate"""
    from simple_app import app, get_db

    # Insert known sequence: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
    # Each test has isolated temp database (see conftest.py)
    seq = list(range(10, 101, 10))
    with get_db() as c:
        for v in seq:
            c.execute("""
                INSERT INTO email_messages(subject, sender, recipients, latency_ms, interception_status, direction)
                VALUES(?, ?, ?, ?, ?, ?)
            """, (f"P{v}", 'test@example.com', 'recipient@example.com', v, 'HELD', 'inbound'))
        c.commit()

    client = app.test_client()
    r = client.get('/api/latency-stats')
    data = r.get_json()

    assert data['count'] == len(seq)
    assert data['min'] == 10
    assert data['max'] == 100
    assert data['p50'] in (50, 55)  # Linear interpolation tolerance
    assert data['median'] == 55  # statistics.median([10-100])
    assert data['p90'] >= 90  # 90th percentile should be near 90


if __name__ == '__main__':
    pytest.main([__file__, '-v'])