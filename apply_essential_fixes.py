#!/usr/bin/env python3
"""Apply essential fixes to interception.py without breaking it"""

# Read the file
with open('app/routes/interception.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports at the top if not already present
if 'from functools import wraps' not in content:
    # Add essential imports after existing imports
    import_addition = """from functools import wraps
import shutil
import threading
from collections import defaultdict
from contextlib import contextmanager
"""
    # Find where to add
    import_end = content.find('bp_interception = Blueprint')
    if import_end != -1:
        content = content[:import_end] + import_addition + '\n' + content[import_end:]

# Add rate limiter class if not present
if 'class RateLimiter:' not in content:
    rate_limiter_code = '''
# Simple rate limiter for API protection
_rate_limit_buckets = defaultdict(lambda: {'count': 0, 'reset_time': 0})

def simple_rate_limit(f):
    """Basic rate limiting decorator - 30 requests per minute"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        import time
        from flask import request, jsonify

        client_id = request.remote_addr
        now = time.time()
        bucket = _rate_limit_buckets[client_id]

        # Reset bucket if time window passed (60 seconds)
        if now > bucket['reset_time']:
            bucket['count'] = 0
            bucket['reset_time'] = now + 60

        # Check rate limit
        if bucket['count'] >= 30:
            wait_time = int(bucket['reset_time'] - now)
            return jsonify({'error': 'Rate limit exceeded', 'retry_after': wait_time}), 429

        bucket['count'] += 1
        return f(*args, **kwargs)
    return wrapped

'''
    # Add before bp_interception definition
    bp_pos = content.find('bp_interception = Blueprint')
    if bp_pos != -1:
        content = content[:bp_pos] + rate_limiter_code + content[bp_pos:]

# Add rate limiting to api_email_edit
if '@simple_rate_limit' not in content:
    content = content.replace(
        '@bp_interception.route(\'/api/email/<int:email_id>/edit\', methods=[\'POST\'])\n@login_required\ndef api_email_edit',
        '@bp_interception.route(\'/api/email/<int:email_id>/edit\', methods=[\'POST\'])\n@login_required\n@simple_rate_limit\ndef api_email_edit'
    )

# Save the file
with open('app/routes/interception.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Applied essential fixes to interception.py")

# Also add database backup directory creation to simple_app.py
with open('simple_app.py', 'r', encoding='utf-8') as f:
    simple_content = f.read()

if 'os.makedirs("database_backups"' not in simple_content:
    # Add at the beginning after imports
    backup_code = '''
# Ensure backup directory exists
import os
os.makedirs("database_backups", exist_ok=True)
os.makedirs("emergency_email_backup", exist_ok=True)
'''
    # Find where to add (after Flask app creation)
    app_create = simple_content.find('app = Flask(__name__)')
    if app_create != -1:
        end_line = simple_content.find('\n', app_create)
        simple_content = simple_content[:end_line+1] + backup_code + simple_content[end_line+1:]

    with open('simple_app.py', 'w', encoding='utf-8') as f:
        f.write(simple_content)

    print("✅ Added backup directory creation to simple_app.py")

print("\n✅ Essential fixes applied successfully!")