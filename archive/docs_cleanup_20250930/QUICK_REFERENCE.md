# (Moved) See archive/root_docs_20250930/QUICK_REFERENCE.md

# Email Management Tool - Quick Reference Guide

## 🚀 Quick Start

```bash
# Start the application
python simple_app.py

# Or use the batch file
scripts/setup/start.bat
```

**Access:** http://localhost:5000
**Login:** admin / admin123

## 📁 Where to Find Things

### Running the Application

- **Main App:** `simple_app.py` (root)
- **Start Scripts:** `scripts/setup/start.bat`
- **Database:** `email_manager.db` (root)
- **Encryption Key:** `key.txt` (root)

### Testing

- **Run All Tests:** `tests/helpers/validate_fixes.py`
- **Unit Tests:** `tests/unit/test_*.py`
- **E2E Tests:** `tests/e2e/playwright_*.py`
- **Test Connections:** `tests/unit/test_all_connections.py`

### Account Management

- **Add Gmail:** `scripts/accounts/add_gmail_account.py`
- **Update Credentials:** `scripts/accounts/update_credentials.py`
- **Verify Password:** `scripts/accounts/verify_app_password.py`

### Database Operations

- **Migrate Schema:** `scripts/database/migrate_database.py`
- **Check Schema:** `scripts/database/check_schema.py`

### Documentation

- **Gmail Setup:** `docs/setup/GMAIL_SETUP_GUIDE.md`
- **Architecture:** `docs/architecture/ARCHITECTURE_AUDIT.md`
- **Test Results:** `archive/test-results/`

### Common Commands

#### Start Application

```bash
cd C:/claude/Email-Management-Tool
python simple_app.py
```

#### Run Tests

```bash
# Test all connections
python tests/unit/test_all_connections.py

# Run E2E tests
python tests/e2e/playwright_e2e_tests.py

# Validate everything
python tests/helpers/final_validation.py
```

#### Add Gmail Account

```bash
python scripts/accounts/add_gmail_account.py
```

#### Check Database

```bash
python scripts/database/check_schema.py
```

## 📂 Directory Structure Overview

```
Email-Management-Tool/
├── simple_app.py          # ← START HERE
├── tests/                 # All test files
│   ├── unit/             # Unit tests
│   ├── e2e/              # Browser tests
│   └── helpers/          # Test utilities
├── scripts/              # Utility scripts
│   ├── setup/            # Batch/PS1 files
│   ├── database/         # DB utilities
│   └── accounts/         # Account tools
├── docs/                 # Documentation
│   ├── setup/            # Setup guides
│   ├── architecture/     # Technical docs
│   └── reports/          # Analysis
└── archive/              # Old files
    ├── test-results/     # JSON results
    └── old-implementations/
```

## 🔧 Troubleshooting

### Can't Find a File?

1. **Tests?** → Check `tests/` subdirectories
2. **Scripts?** → Check `scripts/` subdirectories
3. **Docs?** → Check `docs/` subdirectories
4. **Old stuff?** → Check `archive/`

### Application Won't Start?

1. Ensure you're in the root directory
2. Run: `python simple_app.py`
3. Check `email_manager.db` exists
4. Check `key.txt` exists

### Import Errors?

- All imports should work as before
- Main app (`simple_app.py`) is still in root
- No import path changes needed

---

_Quick Reference Created: September 12, 2025_
