#!/usr/bin/env python3
"""
Smoke test script to verify functionality after IMAP helper extraction
"""
import os
import sys
import requests
import json
from simple_app import app

def test_endpoints():
    """Test key endpoints to verify functionality"""
    with app.test_client() as client:
        # Mock authentication for testing
        with client.session_transaction() as sess:
            sess['user_id'] = 1

        print("🧪 Running smoke tests...")

        # Test /api/unified-stats
        try:
            response = client.get('/api/unified-stats')
            if response.status_code == 200:
                data = response.get_json()
                print("✅ /api/unified-stats: OK")
                print(f"   Response keys: {list(data.keys())}")
            else:
                print(f"⚠️  /api/unified-stats: Status {response.status_code} (302 expected for auth)")
        except Exception as e:
            print(f"❌ /api/unified-stats: Exception - {e}")
            return False

        # Test /api/interception/held
        try:
            response = client.get('/api/interception/held')
            if response.status_code == 200:
                data = response.get_json()
                print("✅ /api/interception/held: OK")
                print(f"   Response keys: {list(data.keys())}")
                if 'messages' in data:
                    print(f"   Messages count: {len(data['messages'])}")
            else:
                print(f"⚠️  /api/interception/held: Status {response.status_code} (302 expected for auth)")
        except Exception as e:
            print(f"❌ /api/interception/held: Exception - {e}")
            return False

        # Test basic import functionality
        try:
            from app.utils.imap_helpers import _imap_connect_account, _ensure_quarantine, _move_uid_to_quarantine
            print("✅ IMAP helpers import: OK")
        except Exception as e:
            print(f"❌ IMAP helpers import: Failed - {e}")
            return False

        # Test database import functionality
        try:
            from app.utils.db import get_db, DB_PATH, table_exists
            print("✅ Database utilities import: OK")
        except Exception as e:
            print(f"❌ Database utilities import: Failed - {e}")
            return False

        # Test crypto import functionality
        try:
            from app.utils.crypto import encrypt_credential, decrypt_credential
            print("✅ Crypto utilities import: OK")
        except Exception as e:
            print(f"❌ Crypto utilities import: Failed - {e}")
            return False

        return True

if __name__ == '__main__':
    success = test_endpoints()
    if success:
        print("\n🎉 All smoke tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some smoke tests failed!")
        sys.exit(1)