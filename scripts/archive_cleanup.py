#!/usr/bin/env python3
import os, json, shutil
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEST = os.path.join(ROOT, 'archive', datetime.now().strftime('%Y-%m-%d') + '_cleanup')
FILES = [
    'app_startup.log',
    'check_workers.py',
    'test_interception_proof.py',
    'test_email_flow.sqlite',
    'test_edit_persistence_final.py',
    'test_edit_debug.py',
    'test_comprehensive_system.py',
    'test_api_performance.py',
    'smoke_test.py',
    'RECOVERY_SUMMARY.md',
    'api_test_results_1760204381.json',
    'test_results_1760204299.json',
]

# include DB backups (variable names) at runtime
for name in os.listdir(ROOT):
    if name.startswith('email_manager.db.backup_'):
        FILES.append(name)

os.makedirs(DEST, exist_ok=True)

moved = []
for rel in FILES:
    src = os.path.join(ROOT, rel)
    if os.path.exists(src):
        dst = os.path.join(DEST, os.path.basename(rel))
        try:
            shutil.move(src, dst)
            moved.append(rel)
        except Exception as e:
            print(f"WARN: failed to move {rel}: {e}")

manifest = {
    'archive_date': datetime.now().strftime('%Y-%m-%d'),
    'target': DEST,
    'files_moved': moved,
}
with open(os.path.join(DEST, 'archives-manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

print(f"Moved {len(moved)} files to {DEST}")
