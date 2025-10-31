# Migration Implementation Checklist

## ✅ Implementation Complete

Use this checklist to verify the migration is ready to use.

---

## Files Created

- ✅ `scripts/migrate_moderation_rules.ps1` - PowerShell migration wrapper
- ✅ `scripts/migrate_moderation_rules.bat` - Batch file migration wrapper
- ✅ `scripts/MIGRATION_GUIDE.md` - Comprehensive documentation
- ✅ `MIGRATION_QUICK_START.md` - Quick reference card
- ✅ `MIGRATION_IMPLEMENTATION_SUMMARY.md` - Implementation details

## Files Modified

- ✅ `simple_app.py` - Updated table creation to include new columns
- ✅ `scripts/fix_database_schema.py` - Enhanced migration script with all 7 columns
- ✅ `README.md` - Added migration section

## Schema Changes

### New Columns Added to moderation_rules Table

- ✅ `rule_type` TEXT DEFAULT 'keyword'
- ✅ `condition_field` TEXT
- ✅ `condition_operator` TEXT
- ✅ `condition_value` TEXT
- ✅ `action` TEXT DEFAULT 'hold' *(updated default)*
- ✅ `priority` INTEGER DEFAULT 100 *(column existed, default updated)*
- ✅ `created_at` TEXT DEFAULT '' *(column existed, included for completeness)*

### Existing Columns Preserved

- ✅ `id` - Primary key
- ✅ `rule_name` - Rule identifier
- ✅ `keyword` - Legacy pattern field (kept for backward compatibility)
- ✅ `is_active` - Enable/disable flag

---

## Testing Checklist

### Pre-Migration Tests

- [ ] Backup your existing database
  ```powershell
  Copy-Item .\email_manager.db .\email_manager.db.backup
  ```

- [ ] Verify current schema
  ```bash
  sqlite3 email_manager.db "PRAGMA table_info(moderation_rules);"
  ```

- [ ] Note number of existing rules
  ```bash
  sqlite3 email_manager.db "SELECT COUNT(*) FROM moderation_rules;"
  ```

### Run Migration

Choose one method:

**Option A: PowerShell (Recommended)**
```powershell
.\scripts\migrate_moderation_rules.ps1
```

**Option B: Batch File**
```cmd
scripts\migrate_moderation_rules.bat
```

**Option C: Direct Python**
```bash
python scripts/fix_database_schema.py
```

### Post-Migration Verification

- [ ] Check migration completed successfully (no errors in output)

- [ ] Verify new columns exist
  ```bash
  sqlite3 email_manager.db "PRAGMA table_info(moderation_rules);" | grep -E "(rule_type|condition_field|condition_operator|condition_value)"
  ```

  Should show:
  - `rule_type | TEXT | 0 | 'keyword' | 0`
  - `condition_field | TEXT | 0 | | 0`
  - `condition_operator | TEXT | 0 | | 0`
  - `condition_value | TEXT | 0 | | 0`

- [ ] Verify data integrity (same number of rules)
  ```bash
  sqlite3 email_manager.db "SELECT COUNT(*) FROM moderation_rules;"
  ```

- [ ] Check existing rules still have their data
  ```bash
  sqlite3 email_manager.db "SELECT id, rule_name, keyword, is_active FROM moderation_rules LIMIT 5;"
  ```

### Application Tests

- [ ] Start the application
  ```cmd
  start.bat
  ```

- [ ] Log in to dashboard (http://localhost:5000)

- [ ] Navigate to Rules page (/rules)

- [ ] Verify existing rules display correctly

- [ ] Create a new rule using the UI
  - [ ] Test with rule_type = "KEYWORD"
  - [ ] Test with rule_type = "SENDER"
  - [ ] Test with rule_type = "REGEX"

- [ ] Edit an existing rule

- [ ] Delete a test rule

- [ ] Verify rule evaluation still works
  - [ ] Create a test rule with a keyword
  - [ ] Send a test email matching that keyword
  - [ ] Verify email is held/filtered correctly

### Rollback Test (Optional)

If you need to rollback:

- [ ] Stop the application

- [ ] Restore backup
  ```powershell
  Copy-Item .\email_manager.db.backup .\email_manager.db -Force
  ```

- [ ] Restart application

- [ ] Verify everything works with old schema

---

## Fresh Installation Test

Test that new installations work without migration:

- [ ] Create a new test directory

- [ ] Copy application files (exclude email_manager.db)

- [ ] Run setup.bat or start.bat

- [ ] Verify database is created with full schema
  ```bash
  sqlite3 email_manager.db "PRAGMA table_info(moderation_rules);"
  ```

- [ ] Should include all new columns from the start

---

## CI/CD Integration

If using CI/CD:

- [ ] Add migration step to CI pipeline (if needed for existing test DBs)
  ```yaml
  - run: python scripts/fix_database_schema.py ./email_manager.db
  ```

- [ ] Verify CI tests pass with new schema

- [ ] Verify CI tests pass with fresh database (no migration)

---

## Documentation Review

- [ ] Read `MIGRATION_QUICK_START.md`

- [ ] Read `scripts/MIGRATION_GUIDE.md`

- [ ] Read `MIGRATION_IMPLEMENTATION_SUMMARY.md`

- [ ] Verify README.md includes migration section

- [ ] Check that all links work

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Test migration on a copy of production database

- [ ] Document rollback procedure

- [ ] Schedule maintenance window (if preferred, though no downtime required)

- [ ] Notify users (optional - transparent upgrade)

- [ ] Create production backup
  ```powershell
  Copy-Item .\email_manager.db ".\backups\email_manager_pre_migration_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
  ```

- [ ] Run migration on production database

- [ ] Verify migration success

- [ ] Start application

- [ ] Monitor logs for errors

- [ ] Test critical workflows

- [ ] Keep backup for 30 days

---

## Troubleshooting

### Common Issues

**Issue: "Python is not in your PATH"**
- [ ] Install Python 3.9+ from python.org
- [ ] OR use PowerShell with `-UseSqlite3` flag

**Issue: "duplicate column name"**
- [ ] This is OK - column already exists
- [ ] Migration will skip it and continue
- [ ] Verify in output that other columns were added

**Issue: "no such table: moderation_rules"**
- [ ] Run the application once to create tables
- [ ] Then run migration

**Issue: Migration script not found**
- [ ] Verify you're in the repository root
- [ ] Check that `scripts/fix_database_schema.py` exists
- [ ] Use full path if needed

---

## Success Criteria

Migration is successful when:

- ✅ All 7 new columns exist in moderation_rules table
- ✅ All existing data is preserved
- ✅ Application starts without errors
- ✅ Rules page displays correctly
- ✅ Can create/edit/delete rules
- ✅ Rule evaluation works correctly
- ✅ Tests pass (if running test suite)

---

## Questions or Issues?

- Review `scripts/MIGRATION_GUIDE.md` for detailed troubleshooting
- Check application logs in `logs/` directory
- Open an issue on GitHub
- Contact the development team

---

**Ready to migrate?** Start with the Pre-Migration Tests above! 🚀
