#!/usr/bin/env python3
"""
Safe Cleanup Script for Email Management Tool
Removes temporary files, cache, and safe-to-delete artifacts
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Define cleanup targets
CLEANUP_TARGETS = {
    'python_cache': {
        'patterns': ['__pycache__', '*.pyc', '*.pyo'],
        'description': 'Python cache files',
        'safe': True
    },
    'pytest_cache': {
        'patterns': ['.pytest_cache'],
        'description': 'Pytest cache directories',
        'safe': True
    },
    'coverage': {
        'patterns': ['.coverage', 'htmlcov', 'coverage.json'],
        'description': 'Coverage report files',
        'safe': True
    },
    'history': {
        'patterns': ['.history'],
        'description': 'VSCode/Cursor history files',
        'safe': True
    },
    'logs_archive': {
        'patterns': ['archive/**/*.log'],
        'description': 'Archived log files',
        'safe': True
    },
    'duplicate_agents': {
        'patterns': ['AGENTS - Copy*.md'],
        'description': 'Duplicate AGENTS.md files',
        'safe': True
    },
    'old_databases': {
        'patterns': [
            'claudeEmail-Management-Toolemail_manager.db',
            'claudeEmail-Management-Tooltest_dashboard.html',
            'email_manager.db.backup_before_rollback',
            'email_manager.db.fresh_empty'
        ],
        'description': 'Old/duplicate database files',
        'safe': False  # Requires review
    }
}


def get_size(path):
    """Get size of file or directory in bytes"""
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_size(entry.path)
        except PermissionError:
            pass
        return total
    return 0


def format_size(bytes_size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def find_files(root_dir, patterns):
    """Find files matching patterns"""
    root_path = Path(root_dir)
    found = []

    for pattern in patterns:
        if '**' in pattern:
            # Recursive glob
            found.extend(root_path.glob(pattern))
        else:
            # Direct match
            if pattern.startswith('*.'):
                # Extension pattern
                found.extend(root_path.rglob(pattern))
            else:
                # Exact name pattern
                found.extend(root_path.rglob(pattern))

    return [str(p) for p in found]


def analyze_cleanup(root_dir, dry_run=True, safe_only=True):
    """Analyze what would be cleaned up"""
    print(f"{'='*60}")
    print(f"Email Management Tool - Cleanup Analysis")
    print(f"{'='*60}")
    print(f"Root: {root_dir}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"Safe only: {safe_only}")
    print(f"{'='*60}\n")

    total_files = 0
    total_size = 0
    cleanup_plan = {}

    for category, config in CLEANUP_TARGETS.items():
        if safe_only and not config['safe']:
            print(f"⏭️  Skipping {category} (requires review)")
            continue

        print(f"📁 Scanning: {config['description']}")
        files = find_files(root_dir, config['patterns'])

        if not files:
            print(f"   ✓ No files found\n")
            continue

        category_size = sum(get_size(f) for f in files if os.path.exists(f))
        cleanup_plan[category] = {
            'files': files,
            'count': len(files),
            'size': category_size,
            'description': config['description']
        }

        total_files += len(files)
        total_size += category_size

        print(f"   Found: {len(files)} items ({format_size(category_size)})")

        # Show first 5 examples
        for f in files[:5]:
            rel_path = os.path.relpath(f, root_dir)
            print(f"   - {rel_path}")

        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more")
        print()

    print(f"{'='*60}")
    print(f"Total: {total_files} items, {format_size(total_size)}")
    print(f"{'='*60}\n")

    return cleanup_plan, total_files, total_size


def execute_cleanup(cleanup_plan, dry_run=True):
    """Execute the cleanup plan"""
    if dry_run:
        print("🔍 DRY RUN - No files will be deleted\n")
        return

    print("🗑️  EXECUTING CLEANUP...\n")

    removed_count = 0
    removed_size = 0
    errors = []

    for category, data in cleanup_plan.items():
        print(f"Cleaning {data['description']}...")

        for file_path in data['files']:
            try:
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    removed_count += 1
                    removed_size += size
                elif os.path.isdir(file_path):
                    size = get_size(file_path)
                    shutil.rmtree(file_path)
                    removed_count += 1
                    removed_size += size
            except Exception as e:
                errors.append((file_path, str(e)))

        print(f"   ✓ Cleaned {len(data['files'])} items\n")

    print(f"{'='*60}")
    print(f"✅ Cleanup complete!")
    print(f"   Removed: {removed_count} items")
    print(f"   Freed: {format_size(removed_size)}")

    if errors:
        print(f"\n⚠️  Errors ({len(errors)}):")
        for path, error in errors[:10]:
            print(f"   - {os.path.basename(path)}: {error}")

    print(f"{'='*60}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Safe cleanup for Email Management Tool')
    parser.add_argument('--execute', action='store_true', help='Execute cleanup (default: dry run)')
    parser.add_argument('--all', action='store_true', help='Include non-safe items (requires review)')
    parser.add_argument('--root', default='.', help='Project root directory')

    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)

    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a valid directory")
        sys.exit(1)

    # Analyze
    cleanup_plan, total_files, total_size = analyze_cleanup(
        root_dir,
        dry_run=not args.execute,
        safe_only=not args.all
    )

    if not cleanup_plan:
        print("✨ Nothing to clean up!")
        return

    # Confirm execution
    if args.execute:
        print("\n⚠️  WARNING: This will permanently delete files!")
        response = input("Continue? (yes/no): ").strip().lower()

        if response != 'yes':
            print("Cancelled.")
            return

        execute_cleanup(cleanup_plan, dry_run=False)
    else:
        print("💡 Run with --execute to perform cleanup")
        print("💡 Run with --all to include non-safe items")


if __name__ == '__main__':
    main()
