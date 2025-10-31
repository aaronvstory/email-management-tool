# Task 17: Attachment Schema Migration - October 31, 2025

## Problem Identified

The `email_attachments` table had an outdated schema causing 500 errors when accessing attachment routes.

### Old Schema (Causing Errors)
```sql
CREATE TABLE email_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    size INTEGER,
    data BLOB,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Issues:**
- Stored attachments as BLOBs in `data` column (scalability issue)
- Used `content_type` instead of `mime_type` (code expected `mime_type`)
- Missing `storage_path` column (code expected file-based storage)
- Missing metadata columns (`is_original`, `is_staged`, `sha256`, etc.)

### New Schema (Fixed)
```sql
CREATE TABLE email_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    filename TEXT,
    mime_type TEXT,
    size INTEGER,
    sha256 TEXT,
    disposition TEXT,
    content_id TEXT,
    is_original BOOLEAN DEFAULT 1,
    is_staged BOOLEAN DEFAULT 0,
    storage_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(email_id) REFERENCES email_messages(id) ON DELETE CASCADE
);

CREATE INDEX idx_attachments_email_id ON email_attachments(email_id);
```

## Migration Steps Performed

1. **Verified no existing data**: Confirmed 0 attachments in database
   ```bash
   sqlite3 email_manager.db "SELECT COUNT(*) FROM email_attachments;"
   # Result: 0
   ```

2. **Dropped old table**:
   ```bash
   sqlite3 email_manager.db "DROP TABLE IF EXISTS email_attachments;"
   ```

3. **Created new table** with correct schema matching code expectations

4. **Created index** for performance:
   ```sql
   CREATE INDEX idx_attachments_email_id ON email_attachments(email_id);
   ```

## Code Fixes

### File: `app/routes/emails.py` (Line 143)
**Before**:
```python
SELECT id, filename, size, content_type
FROM email_attachments
```

**After**:
```python
SELECT id, filename, size, mime_type
FROM email_attachments
```

## Testing Results

- ✅ All 34 route tests passing
- ✅ Schema matches code expectations
- ✅ Error handling verified in `attachment_download()` function
- ✅ No regressions introduced

## Impact

- **Fixes**: 500 errors when accessing `/email/<id>/attachments/<name>` route
- **Enables**: File-based attachment storage (scalable)
- **Supports**: Advanced attachment features (staging, versioning, manifest)
- **Performance**: Indexed `email_id` lookups

## Future Considerations

- Attachments will now be stored as files on disk in `attachments/` directory
- Each email's attachments stored in `attachments/<email_id>/` subdirectory
- Staged attachments go to `attachments_staged/` during editing
- Schema supports versioning and manifest-based attachment management

## Related Files

- `create_missing_tables.py` - Migration script template (not used due to IF NOT EXISTS issue)
- `app/routes/interception.py` - Lines 1088-1126: `attachment_download()` function
- `app/routes/emails.py` - Line 141-149: Attachment query fixed

## Commit

Commit: [To be added after commit]
