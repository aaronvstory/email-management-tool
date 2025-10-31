# Database Schema Migration - Quick Start

## Add Missing Columns to moderation_rules Table

The application code already supports both legacy and extended schemas. Run this migration to add the new columns to your existing database.

### Quick Commands

**Windows (PowerShell) - Recommended:**
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

### What This Does

Adds these columns to `moderation_rules` table:
- `rule_type` - Type of rule (KEYWORD, SENDER, REGEX, etc.)
- `condition_field` - Which field to check (SUBJECT, BODY, SENDER, etc.)
- `condition_operator` - How to match (CONTAINS, REGEX, EQUALS, etc.)
- `condition_value` - Value to match
- `action` - What to do (HOLD, APPROVE, REJECT, etc.)
- `priority` - Rule priority (0-100)
- `created_at` - Timestamp

### Safety

✅ Safe to run multiple times (skips existing columns)
✅ Keeps all existing data
✅ Backward compatible
✅ No downtime needed

### More Info

See `scripts/MIGRATION_GUIDE.md` for detailed documentation.
