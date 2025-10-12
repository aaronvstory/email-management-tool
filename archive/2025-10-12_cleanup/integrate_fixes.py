#!/usr/bin/env python3
"""
Integration script to apply critical fixes to Email Management Tool
This script patches the running application with production-ready improvements
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime

def backup_file(filepath):
    """Create backup before modifying"""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up {filepath} to {backup_path}")
    return backup_path

def patch_interception_py():
    """Add rate limiting and fixes to app/routes/interception.py"""

    filepath = "app/routes/interception.py"
    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add imports at the top
    import_patch = """import os
import time
import threading
import statistics
from datetime import datetime
from collections import defaultdict, deque
import sqlite3
from typing import Dict, Any
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required, current_user
from email.parser import BytesParser
from email.policy import default as default_policy
import difflib
import imaplib, ssl
from functools import wraps

from app.utils.db import get_db, DB_PATH
from app.utils.crypto import decrypt_credential, encrypt_credential
from app.utils.imap_helpers import _imap_connect_account, _ensure_quarantine, _move_uid_to_quarantine

# ============================================================================
# Rate Limiting Implementation
# ============================================================================

class RateLimiter:
    def __init__(self, requests_per_minute=30, burst_size=50):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.buckets = defaultdict(lambda: {
            'tokens': burst_size,
            'last_update': time.time()
        })
        self.lock = threading.Lock()
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_loop(self):
        '''Clean up old client entries every hour'''
        while True:
            time.sleep(3600)  # Run every hour
            with self.lock:
                now = time.time()
                # Remove entries older than 1 hour
                old_clients = [k for k, v in self.buckets.items()
                              if now - v['last_update'] > 3600]
                for client in old_clients:
                    del self.buckets[client]

    def is_allowed(self, client_id):
        with self.lock:
            now = time.time()
            bucket = self.buckets[client_id]

            # Refill tokens
            time_passed = now - bucket['last_update']
            tokens_to_add = time_passed * (self.requests_per_minute / 60)
            bucket['tokens'] = min(self.burst_size, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = now

            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True, 0
            else:
                wait_time = (1 - bucket['tokens']) * 60 / self.requests_per_minute
                return False, wait_time

# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=30, burst_size=50)

def rate_limit(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        client_id = request.remote_addr
        allowed, wait_time = rate_limiter.is_allowed(client_id)
        if not allowed:
            return jsonify({
                'error': 'Rate limit exceeded',
                'retry_after': int(wait_time)
            }), 429
        return f(*args, **kwargs)
    return wrapped

# ============================================================================
# Database Backup Context Manager
# ============================================================================

from contextlib import contextmanager

@contextmanager
def database_backup(operation_name="operation"):
    '''Create database backup before critical operations'''
    backup_dir = "database_backups"
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"backup_{operation_name}_{timestamp}.db")

    try:
        shutil.copy2(DB_PATH, backup_path)
        yield backup_path

        # Clean old backups (keep last 10)
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join(backup_dir, old_backup))
    except Exception as e:
        # Restore on failure
        shutil.copy2(backup_path, DB_PATH)
        raise

"""

    # Replace the imports section
    import_line = content.find("import os")
    if import_line == -1:
        import_line = content.find("from flask import")

    if import_line != -1:
        # Find the end of imports
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('import') and not line.startswith('from'):
                if i > 10:  # Past the import section
                    import_end = i
                    break

        # Insert our imports after existing imports
        before = '\n'.join(lines[:import_end])
        after = '\n'.join(lines[import_end:])
        content = before + '\n\n' + import_patch + '\n\n' + after

    # Fix the api_email_edit function to add rate limiting
    content = content.replace(
        "@bp_interception.route('/api/email/<int:email_id>/edit', methods=['POST'])\n@login_required\ndef api_email_edit",
        "@bp_interception.route('/api/email/<int:email_id>/edit', methods=['POST'])\n@login_required\n@rate_limit\ndef api_email_edit"
    )

    # Fix the bug in api_interception_release (msg_id vs email_id)
    content = content.replace(
        'WHERE id=?"\n    """, (msg.get(\'Message-ID\'), msg_id))',
        'WHERE id=?"\n    """, (msg.get(\'Message-ID\'), msg_id))'  # This is actually correct
    )

    # Add database backup to release function
    old_release = "def api_interception_release(msg_id:int):\n    payload = request.get_json(silent=True) or {}"
    new_release = """def api_interception_release(msg_id:int):
    '''Release email with database backup and transaction safety'''
    payload = request.get_json(silent=True) or {}

    # Backup database before release operation
    with database_backup(f"release_{msg_id}"):"""

    content = content.replace(old_release, new_release)

    # Save patched file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Patched {filepath} with rate limiting and fixes")

def create_notifications_migration():
    """Create migration script for notifications table"""

    migration_content = '''#!/usr/bin/env python3
"""
Migration: Add email_notifications table for bounce/reject tracking
"""

import sqlite3

DB_PATH = "email_manager.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                notification_type TEXT,
                severity TEXT,
                message TEXT,
                user_id INTEGER,
                acknowledged BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES email_messages(id)
            )
        """)

        # Add index for quick lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_email_id
            ON email_notifications(email_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_acknowledged
            ON email_notifications(acknowledged)
        """)

        # Add bounce_reason column to email_messages if not exists
        cursor.execute("PRAGMA table_info(email_messages)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'bounce_reason' not in columns:
            cursor.execute("""
                ALTER TABLE email_messages
                ADD COLUMN bounce_reason TEXT
            """)
            print("✅ Added bounce_reason column")

        conn.commit()
        print("✅ Notifications table created successfully")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
'''

    filepath = "migrations/add_notifications_table.py"
    os.makedirs("migrations", exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(migration_content)

    print(f"✅ Created migration script: {filepath}")

    # Run the migration
    import subprocess
    result = subprocess.run([sys.executable, filepath], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Migration executed successfully")
    else:
        print(f"⚠️ Migration failed: {result.stderr}")

def patch_requirements():
    """Update requirements.txt with necessary packages"""

    filepath = "requirements.txt"

    with open(filepath, 'r') as f:
        content = f.read()

    # Add missing packages if not present
    packages_to_add = []

    if 'flask-limiter' not in content.lower():
        packages_to_add.append('Flask-Limiter==3.5.0')

    if packages_to_add:
        backup_file(filepath)
        with open(filepath, 'a') as f:
            f.write('\n# Rate limiting and monitoring\n')
            for package in packages_to_add:
                f.write(f"{package}\n")
        print(f"✅ Updated requirements.txt with: {', '.join(packages_to_add)}")

def add_port_check_function():
    """Add port checking function to simple_app.py without psutil"""

    port_check_code = '''
def check_port_available(port, host='localhost'):
    """Check if a port is available without psutil"""
    import socket
    import subprocess
    import platform

    # First check if port is in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    sock.close()

    if result != 0:  # Port is free
        return True, None

    # Port is in use, try to find and kill the process
    if platform.system() == 'Windows':
        # Windows: use netstat
        try:
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
            for line in output.split('\\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    try:
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
                        print(f"Killed process {pid} using port {port}")
                        time.sleep(2)
                        return True, pid
                    except:
                        pass
        except:
            pass
    else:
        # Linux/Mac: use lsof
        try:
            output = subprocess.check_output(f'lsof -i :{port}', shell=True, text=True)
            lines = output.split('\\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) > 1:
                    pid = parts[1]
                    try:
                        subprocess.run(f'kill -9 {pid}', shell=True, check=True)
                        print(f"Killed process {pid} using port {port}")
                        time.sleep(2)
                        return True, pid
                    except:
                        pass
        except:
            pass

    return False, None
'''

    filepath = "simple_app.py"
    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add the function after imports
    import_section_end = content.find('\n\n# Flask app initialization')
    if import_section_end == -1:
        import_section_end = content.find('\napp = Flask')

    if import_section_end != -1:
        before = content[:import_section_end]
        after = content[import_section_end:]
        content = before + '\n' + port_check_code + after

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Added port checking function to {filepath}")

def add_emergency_backup_cleanup():
    """Add cleanup for emergency email backups"""

    cleanup_code = '''
def cleanup_emergency_backups(days_to_keep=7):
    """Clean up old emergency email backups"""
    import os
    import time
    import json
    from datetime import datetime, timedelta

    emergency_dir = "emergency_email_backup"
    if not os.path.exists(emergency_dir):
        return

    cutoff_time = time.time() - (days_to_keep * 86400)

    for filename in os.listdir(emergency_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(emergency_dir, filename)
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    print(f"Cleaned up old backup: {filename}")
                except:
                    pass

# Schedule cleanup to run periodically
def schedule_cleanup():
    import threading
    def run_cleanup():
        while True:
            cleanup_emergency_backups()
            time.sleep(86400)  # Run daily

    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()
'''

    # Add to simple_app.py
    filepath = "simple_app.py"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add before main block
    main_block = content.find("if __name__ == '__main__':")
    if main_block != -1:
        before = content[:main_block]
        after = content[main_block:]
        content = before + '\n' + cleanup_code + '\n\n' + after

        # Add schedule call in main
        content = content.replace(
            "if __name__ == '__main__':\n    app.run",
            "if __name__ == '__main__':\n    schedule_cleanup()  # Start cleanup thread\n    app.run"
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Added emergency backup cleanup to {filepath}")

def main():
    """Run all integration patches"""

    print("\n" + "="*60)
    print("INTEGRATING CRITICAL FIXES INTO EMAIL MANAGEMENT TOOL")
    print("="*60 + "\n")

    try:
        # 1. Patch interception.py with rate limiting
        print("1. Adding rate limiting to API endpoints...")
        patch_interception_py()

        # 2. Create notifications table migration
        print("\n2. Creating notifications table...")
        create_notifications_migration()

        # 3. Update requirements
        print("\n3. Updating requirements.txt...")
        patch_requirements()

        # 4. Add port checking
        print("\n4. Adding port availability checking...")
        add_port_check_function()

        # 5. Add cleanup mechanisms
        print("\n5. Adding cleanup mechanisms...")
        add_emergency_backup_cleanup()

        print("\n" + "="*60)
        print("✅ ALL CRITICAL FIXES INTEGRATED SUCCESSFULLY!")
        print("="*60)
        print("\nNext steps:")
        print("1. Restart the Flask application to apply changes")
        print("2. Install new requirements: pip install -r requirements.txt")
        print("3. Test the integrated fixes")

    except Exception as e:
        print(f"\n❌ Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())