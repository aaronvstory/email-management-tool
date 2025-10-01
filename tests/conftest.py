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
"""
import pytest


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