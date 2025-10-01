"""
Tests for Rapid IMAP Copy+Purge Worker

These are structural tests to verify imports and basic instantiation.
Full integration tests require live IMAP server access.
"""

import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_import_worker():
    """Test that RapidCopyPurgeWorker can be imported"""
    from app.services.interception.rapid_imap_copy_purge import RapidCopyPurgeWorker
    assert RapidCopyPurgeWorker is not None


def test_worker_instantiation():
    """Test that worker can be instantiated with valid parameters"""
    from app.services.interception.rapid_imap_copy_purge import RapidCopyPurgeWorker
    
    worker = RapidCopyPurgeWorker(
        account_id=1,
        imap_host="imap.example.com",
        imap_port=993,
        username="test@example.com",
        password="password123",
        use_ssl=True,
        quarantine_folder="InterceptHold"
    )
    
    assert worker.account_id == 1
    assert worker.imap_host == "imap.example.com"
    assert worker.quarantine == "InterceptHold"
    assert worker.daemon is True  # Should be daemon thread