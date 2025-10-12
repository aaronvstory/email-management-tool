#!/usr/bin/env python3
"""
Workspace cleanup script (safe):
- Remove cache dirs: __pycache__, .pytest_cache, .mypy_cache
- Remove compiled files: *.pyc, *.pyo
- Move test DB artifacts to archive/cleanup_databases/<timestamp>

Run: python scripts/cleanup_workspace.py
"""
import os, sys, shutil, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_BASE = PROJECT_ROOT / 'archive' / 'cleanup_databases'

CACHE_DIR_NAMES = {'__pycache__', '.pytest_cache', '.mypy_cache'}
CACHE_FILE_SUFFIXES = {'.pyc', '.pyo'}
DB_FILES = {'test_intercept_flow.db', 'test_email_flow.sqlite'}

removed_dirs = []
removed_files = []
archived_dbs = []


def safe_is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def remove_dir(d: Path):
    try:
        shutil.rmtree(d)
        removed_dirs.append(str(d.relative_to(PROJECT_ROOT)))
    except Exception as e:
        print(f"WARN: failed to remove dir {d}: {e}")


def remove_file(f: Path):
    try:
        f.unlink(missing_ok=True)
        removed_files.append(str(f.relative_to(PROJECT_ROOT)))
    except Exception as e:
        print(f"WARN: failed to remove file {f}: {e}")


def archive_db(f: Path):
    ts = time.strftime('%Y%m%d_%H%M%S')
    dest_dir = ARCHIVE_BASE / ts
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f.name
    try:
        shutil.move(str(f), str(dest))
        archived_dbs.append(str(dest.relative_to(PROJECT_ROOT)))
    except Exception as e:
        print(f"WARN: failed to archive db {f}: {e}")


def main():
    if not safe_is_within(PROJECT_ROOT, PROJECT_ROOT):
        print('Invalid project root context')
        sys.exit(2)
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Prune .git and archive
        dirs[:] = [d for d in dirs if d not in {'.git'}]
        p_root = Path(root)
        # Remove cache dirs
        for d in list(dirs):
            if d in CACHE_DIR_NAMES:
                target = p_root / d
                if safe_is_within(target, PROJECT_ROOT):
                    remove_dir(target)
                # prevent os.walk from descending
                try:
                    dirs.remove(d)
                except ValueError:
                    pass
        # Remove cache files & archive test DBs
        for name in files:
            p = p_root / name
            if p.suffix in CACHE_FILE_SUFFIXES:
                remove_file(p)
            elif name in DB_FILES:
                archive_db(p)
    print('\nCleanup summary:')
    print('  Removed dirs:', len(removed_dirs))
    print('  Removed files:', len(removed_files))
    print('  Archived DBs:', len(archived_dbs))
    if archived_dbs:
        print('  DB archive dests:')
        for d in archived_dbs:
            print('   -', d)


if __name__ == '__main__':
    main()
