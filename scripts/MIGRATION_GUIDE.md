# Moderation Rules Schema Migration

## Overview

This migration adds extended schema columns to the `moderation_rules` table while keeping the legacy keyword-based columns intact. This allows the application to work with both old and new data formats seamlessly.

## New Columns Added

| Column Name | Type | Default | Description |
|------------|------|---------|-------------|
| `rule_type` | TEXT | 'keyword' | Type of rule: KEYWORD, SENDER, RECIPIENT, ATTACHMENT, SIZE, REGEX, DOMAIN, CONTENT |
| `condition_field` | TEXT | NULL | Field to check: SUBJECT, BODY, SENDER, RECIPIENT, ATTACHMENT, etc. |
| `condition_operator` | TEXT | NULL | Operator: CONTAINS, REGEX, EQUALS, STARTS_WITH, ENDS_WITH |
| `condition_value` | TEXT | NULL | Value to match against |
| `action` | TEXT | 'hold' | Action to take: HOLD, APPROVE, REJECT, QUARANTINE, FLAG |
| `priority` | INTEGER | 100 | Rule priority (0-100, higher = more important) |
| `created_at` | TEXT | '' | Timestamp when rule was created |

## Running the Migration

### Option 1: Using Python (Recommended)

**Windows (PowerShell):**
```powershell
.\scripts\migrate_moderation_rules.ps1
```

**Windows (Command Prompt):**
```cmd
scripts\migrate_moderation_rules.bat
```

**Linux/macOS:**
```bash
python3 scripts/fix_database_schema.py
```

### Option 2: Using sqlite3 Command-Line Tool

**Windows (PowerShell):**
```powershell
.\scripts\migrate_moderation_rules.ps1 -UseSqlite3
```

**Manual SQL (any platform):**
```bash
sqlite3 email_manager.db << 'EOF'
ALTER TABLE moderation_rules ADD COLUMN rule_type TEXT DEFAULT 'keyword';
ALTER TABLE moderation_rules ADD COLUMN condition_field TEXT;
ALTER TABLE moderation_rules ADD COLUMN condition_operator TEXT;
ALTER TABLE moderation_rules ADD COLUMN condition_value TEXT;
ALTER TABLE moderation_rules ADD COLUMN action TEXT DEFAULT 'hold';
ALTER TABLE moderation_rules ADD COLUMN priority INTEGER DEFAULT 100;
ALTER TABLE moderation_rules ADD COLUMN created_at TEXT DEFAULT '';
EOF
```

### Custom Database Path

If your database is in a different location:

**PowerShell:**
```powershell
.\scripts\migrate_moderation_rules.ps1 -DatabasePath ".\data\email_manager.db"
```

**Command Prompt:**
```cmd
scripts\migrate_moderation_rules.bat ".\data\email_manager.db"
```

**Python:**
```bash
python scripts/fix_database_schema.py ./data/email_manager.db
```

## Migration Safety

✅ **Safe to run multiple times** - The script checks for existing columns and skips them
✅ **Non-destructive** - Keeps all existing data and columns intact
✅ **Backward compatible** - App works with both old and new formats
✅ **No downtime required** - Can run while app is stopped

## Verification

After running the migration, verify the schema:

```bash
sqlite3 email_manager.db ".schema moderation_rules"
```

Expected output should include the new columns:
```sql
CREATE TABLE moderation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT NOT NULL,
    keyword TEXT,  -- Legacy column (kept for backward compatibility)
    is_active INTEGER DEFAULT 1,
    -- New extended schema columns:
    rule_type TEXT DEFAULT 'keyword',
    condition_field TEXT,
    condition_operator TEXT,
    condition_value TEXT,
    action TEXT DEFAULT 'hold',
    priority INTEGER DEFAULT 100,
    created_at TEXT DEFAULT ''
);
```

## How the Code Handles Both Schemas

The application code in `app/routes/moderation.py` automatically detects which columns are available and adapts:

1. **Legacy Schema Detection**: Checks for `rule_type` and `condition_value` columns
2. **Normalization**: Converts data to a common format for templates
3. **Backward Compatibility**: Falls back to `keyword` column if extended columns don't exist
4. **Insert/Update Logic**: Uses appropriate columns based on schema version

Example from code:
```python
# Check which columns exist
cols = [r[1] for r in cursor.execute("PRAGMA table_info(moderation_rules)").fetchall()]

if 'rule_type' in cols and 'condition_value' in cols:
    # Use extended schema
    cursor.execute("""
        INSERT INTO moderation_rules
        (rule_name, rule_type, condition_field, condition_operator, condition_value, action, priority, is_active)
        VALUES(?, ?, ?, ?, ?, ?, ?, 1)
    """, ...)
else:
    # Use legacy schema
    cursor.execute("""
        INSERT INTO moderation_rules
        (rule_name, keyword, action, priority, is_active)
        VALUES(?, ?, ?, ?, 1)
    """, ...)
```

## CI/CD Considerations

### For Fresh Test Databases

If your CI creates fresh test databases, the new schema will be created automatically by SQLAlchemy when tables are created. No migration needed.

### For Existing Test Databases

Add a migration step to your CI pipeline:

```yaml
# Example GitHub Actions
- name: Migrate database schema
  run: python scripts/fix_database_schema.py ./test_db.db
```

```yaml
# Example GitLab CI
migrate:
  script:
    - python3 scripts/fix_database_schema.py ./email_manager.db
```

## Troubleshooting

### Error: "no such table: moderation_rules"
The table doesn't exist yet. Run your app once to create it via SQLAlchemy, then run the migration.

### Error: "duplicate column name"
The column already exists - this is OK! The script will skip it and continue.

### Error: "Python is not in your PATH"
Install Python or use the sqlite3 command-line tool option.

### Error: "sqlite3 is not in your PATH"
Install sqlite3 or use the Python script option (recommended).

## Rollback

If you need to rollback (not recommended as it loses data):

```sql
-- WARNING: This will lose data in the new columns!
-- Backup your database first!

-- SQLite doesn't support DROP COLUMN directly, need to recreate table
-- See: https://www.sqlite.org/lang_altertable.html
```

Instead, it's safer to just restore from a backup if needed.

## Questions?

See the repository's main README or open an issue on GitHub.
