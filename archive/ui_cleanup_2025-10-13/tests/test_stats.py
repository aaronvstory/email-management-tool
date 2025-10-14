"""Test suite for stats service caching (Phase 1 Structural Split)

Tests the app/services/stats.py module including:
- Cache TTL behavior (2-second expiration)
- Force refresh functionality
- Cache metadata introspection
- Clear cache operation

NOTE: Similar to test_counts.py, these tests use the actual database
due to fetch_counts() dependency on get_db(). Tests validate caching
behavior rather than exact count values.
"""
import pytest
import time
from app.services.stats import get_stats, clear_cache, get_cache_info


def test_get_stats_returns_dict():
    """Test that get_stats returns a dictionary with expected keys"""
    stats = get_stats(force_refresh=True)

    assert isinstance(stats, dict), "get_stats should return a dict"
    assert 'total' in stats, "Stats should include 'total'"
    assert 'pending' in stats, "Stats should include 'pending'"
    assert 'approved' in stats, "Stats should include 'approved'"
    assert 'rejected' in stats, "Stats should include 'rejected'"
    assert 'sent' in stats, "Stats should include 'sent'"
    assert 'held' in stats, "Stats should include 'held'"


def test_cache_ttl_behavior():
    """Test that cache expires after TTL (2 seconds)"""
    # Clear any existing cache
    clear_cache()

    # First call - cache miss
    stats1 = get_stats()
    cache_info1 = get_cache_info()
    assert cache_info1['is_valid'], "Cache should be valid immediately after fetch"
    assert cache_info1['age_seconds'] < 0.1, "Cache age should be near zero"

    # Second call - cache hit (within TTL)
    stats2 = get_stats()
    assert stats1 == stats2, "Cached stats should match original"
    cache_info2 = get_cache_info()
    assert cache_info2['is_valid'], "Cache should still be valid within TTL"

    # Wait for TTL expiration
    time.sleep(2.1)
    cache_info3 = get_cache_info()
    assert not cache_info3['is_valid'], "Cache should be invalid after TTL"
    assert cache_info3['age_seconds'] > 2.0, "Cache age should exceed TTL"


def test_force_refresh():
    """Test that force_refresh bypasses cache"""
    clear_cache()

    # Populate cache
    stats1 = get_stats()

    # Small delay to age the cache
    time.sleep(0.2)

    # Normal call should use cached data (age ~0.2s)
    cache_info_before = get_cache_info()
    assert cache_info_before['age_seconds'] >= 0.15, "Cache should have aged"

    # Force refresh should reset cache timestamp
    stats2 = get_stats(force_refresh=True)
    cache_info_after = get_cache_info()

    assert cache_info_after['age_seconds'] < 0.1, "Force refresh should create fresh cache"


def test_clear_cache():
    """Test that clear_cache invalidates cached data"""
    # Populate cache
    stats = get_stats(force_refresh=True)
    cache_info_before = get_cache_info()
    assert cache_info_before['has_data'], "Cache should have data before clear"

    # Clear cache
    clear_cache()
    cache_info_after = get_cache_info()

    assert not cache_info_after['is_valid'], "Cache should be invalid after clear"
    assert not cache_info_after['has_data'], "Cache should have no data after clear"
    assert cache_info_after['age_seconds'] > 10000, "Cache age should be very large (now - 0)"


def test_cache_info_structure():
    """Test that get_cache_info returns expected structure"""
    clear_cache()
    info = get_cache_info()

    assert isinstance(info, dict), "Cache info should be a dict"
    assert 'age_seconds' in info, "Should include age_seconds"
    assert 'is_valid' in info, "Should include is_valid"
    assert 'has_data' in info, "Should include has_data"
    assert isinstance(info['age_seconds'], float), "age_seconds should be float"
    assert isinstance(info['is_valid'], bool), "is_valid should be boolean"
    assert isinstance(info['has_data'], bool), "has_data should be boolean"


def test_concurrent_cache_reads():
    """Test that multiple rapid reads return consistent cached data"""
    clear_cache()

    # First call to populate cache
    stats1 = get_stats()

    # Rapid sequential reads (simulates concurrent access pattern)
    results = [get_stats() for _ in range(10)]

    # All results should match the first (cached) result
    for stats in results:
        assert stats == stats1, "All cached reads should return identical data"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
