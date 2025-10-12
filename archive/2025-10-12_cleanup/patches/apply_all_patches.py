#!/usr/bin/env python3
"""
Master patch application script for Email Management Tool
Applies all critical fixes in correct order with validation
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Color codes for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{text:^80}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def check_prerequisites():
    """Check if git is available and we're in the right directory"""
    print_header("Checking Prerequisites")

    # Check if git is available
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        print_success("Git is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Git is not installed or not in PATH")
        return False

    # Check if we're in the right directory
    if not os.path.exists('simple_app.py'):
        print_error("Not in Email Management Tool root directory")
        print_error(f"Current directory: {os.getcwd()}")
        print_error("Please run from C:\\claude\\Email-Management-Tool")
        return False

    print_success("In correct directory")

    # Check if patches directory exists
    if not os.path.exists('patches'):
        print_error("Patches directory not found")
        return False

    print_success("Patches directory found")
    return True

def create_backup():
    """Create full backup before applying patches"""
    print_header("Creating Backup")

    backup_dir = f"backup_before_patches_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # Backup database
        if os.path.exists('email_manager.db'):
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2('email_manager.db', os.path.join(backup_dir, 'email_manager.db'))
            print_success(f"Database backed up to {backup_dir}/")

        # Backup key files
        files_to_backup = [
            'simple_app.py',
            'app/routes/interception.py',
            'app/services/imap_watcher.py'
        ]

        for file in files_to_backup:
            if os.path.exists(file):
                backup_path = os.path.join(backup_dir, file)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(file, backup_path)
                print_success(f"Backed up {file}")

        print_success(f"Full backup created: {backup_dir}/")
        return backup_dir

    except Exception as e:
        print_error(f"Backup failed: {e}")
        return None

def apply_patch(patch_file, description):
    """Apply a single patch file"""
    print(f"\n{BLUE}Applying:{RESET} {description}")
    print(f"  File: {patch_file}")

    try:
        # Check if patch file exists
        if not os.path.exists(patch_file):
            print_error(f"Patch file not found: {patch_file}")
            return False

        # Try to apply patch
        result = subprocess.run(
            ['git', 'apply', '--check', patch_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print_warning("Dry-run failed, attempting force apply...")
            print(f"  Error: {result.stderr}")

            # Try with --reject to create reject files
            result = subprocess.run(
                ['git', 'apply', '--reject', patch_file],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print_error(f"Failed to apply patch")
                print(f"  Error: {result.stderr}")
                return False

        # Apply patch for real
        result = subprocess.run(
            ['git', 'apply', patch_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print_success(f"Successfully applied")
            return True
        else:
            print_error(f"Failed to apply")
            print(f"  Error: {result.stderr}")
            return False

    except Exception as e:
        print_error(f"Error applying patch: {e}")
        return False

def run_migration(migration_file):
    """Run a database migration script"""
    print(f"\n{BLUE}Running migration:{RESET} {migration_file}")

    try:
        result = subprocess.run(
            ['python', migration_file],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(result.stdout)

        if result.returncode == 0:
            print_success("Migration completed")
            return True
        else:
            print_error("Migration failed")
            print(result.stderr)
            return False

    except Exception as e:
        print_error(f"Error running migration: {e}")
        return False

def verify_integration():
    """Verify patches were applied correctly"""
    print_header("Verifying Integration")

    checks = [
        ('Database backups directory', 'database_backups'),
        ('Emergency backup directory', 'emergency_email_backup'),
        ('IMAP pool module', 'app/utils/imap_pool.py'),
        ('Migration script', 'scripts/migrations/20251011_add_notifications_table.py'),
    ]

    all_passed = True

    for check_name, path in checks:
        if os.path.exists(path):
            print_success(f"{check_name}: {path}")
        else:
            print_warning(f"{check_name}: Not found (expected: {path})")
            all_passed = False

    # Check if key functions were added
    print("\n" + BLUE + "Checking code integration..." + RESET)

    code_checks = [
        ('app/routes/interception.py', 'limiter.limit'),
        ('app/routes/interception.py', '_create_backup'),
        ('simple_app.py', 'is_port_in_use'),
        ('simple_app.py', 'SMTP_HEALTH'),
    ]

    for file_path, search_string in code_checks:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if search_string in content:
                    print_success(f"{file_path}: Contains '{search_string}'")
                else:
                    print_warning(f"{file_path}: Missing '{search_string}'")
                    all_passed = False
        else:
            print_error(f"{file_path}: File not found")
            all_passed = False

    return all_passed

def main():
    """Main patch application workflow"""
    print_header("Email Management Tool - Critical Fixes Integration")
    print("This script will apply 9 critical patches to improve reliability and performance.")
    print("\nPatches to be applied:")
    print("  1. Rate limiting with automatic cleanup")
    print("  2. Port conflict detection (no psutil)")
    print("  3. Database backup before operations")
    print("  4. Idempotent and transactional release")
    print("  5. Emergency email backup system")
    print("  6. Notification system migration")
    print("  7. Fix msg_id vs email_id bug")
    print("  8. IMAP connection pooling")
    print("  9. SMTP health monitoring")

    response = input("\nProceed with patch application? (y/N): ")
    if response.lower() != 'y':
        print("Aborted by user")
        return 1

    # Check prerequisites
    if not check_prerequisites():
        print_error("\nPrerequisite checks failed. Please fix issues and try again.")
        return 1

    # Create backup
    backup_dir = create_backup()
    if not backup_dir:
        print_error("\nBackup failed. Aborting for safety.")
        return 1

    # Apply patches in order
    print_header("Applying Patches")

    patches = [
        ('patches/02_port_check_without_psutil.patch', 'Port conflict detection'),
        ('patches/03_database_backup_integration.patch', 'Database backup system'),
        ('patches/05_emergency_email_backup.patch', 'Emergency email backup'),
        ('patches/04_release_idempotent_transactional.patch', 'Idempotent release'),
        ('patches/07_fix_release_msg_id_bug.patch', 'Fix msg_id bug'),
        ('patches/01_rate_limiting_integration.patch', 'Rate limiting'),
        ('patches/08_imap_connection_pooling.patch', 'Connection pooling'),
        ('patches/09_smtp_health_monitoring.patch', 'Health monitoring'),
    ]

    failed_patches = []

    for patch_file, description in patches:
        if not apply_patch(patch_file, description):
            failed_patches.append((patch_file, description))
            print_warning(f"Continuing with remaining patches...")

    # Run migration
    print_header("Running Database Migration")

    # First, extract migration from patch 06
    migration_patch = 'patches/06_notification_system_migration.patch'
    if os.path.exists(migration_patch):
        print("Extracting migration script from patch...")
        # Apply patch 06 to create migration file
        apply_patch(migration_patch, 'Notification system migration')

    # Run migration if it exists
    migration_script = 'scripts/migrations/20251011_add_notifications_table.py'
    if os.path.exists(migration_script):
        if not run_migration(migration_script):
            print_warning("Migration failed but continuing...")
    else:
        print_warning(f"Migration script not found: {migration_script}")

    # Verify integration
    if not verify_integration():
        print_warning("\nSome verification checks failed")

    # Summary
    print_header("Integration Summary")

    if failed_patches:
        print_error(f"{len(failed_patches)} patches failed to apply:")
        for patch_file, description in failed_patches:
            print(f"  - {description} ({patch_file})")
        print(f"\n{YELLOW}Manual integration may be required for failed patches.{RESET}")
        print(f"See patches/README_INTEGRATION.md for details.")
    else:
        print_success("All patches applied successfully!")

    print(f"\n{GREEN}Backup created:{RESET} {backup_dir}/")
    print(f"\n{BLUE}Next steps:{RESET}")
    print("  1. Review changes: git diff")
    print("  2. Test application: python simple_app.py")
    print("  3. Run tests: python -m pytest tests/ -v")
    print("  4. Check health: curl http://localhost:5000/healthz")
    print(f"\n{YELLOW}To rollback:{RESET}")
    print(f"  cp {backup_dir}/email_manager.db email_manager.db")
    print(f"  git reset --hard HEAD")

    return 0 if not failed_patches else 1

if __name__ == '__main__':
    sys.exit(main())
