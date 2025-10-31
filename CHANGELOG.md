# Changelog

All notable changes to the Email Management Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.10.0] - 2025-10-31

### Added - Task 20: Attachment Storage Cleanup
- **File Deletion on Email Removal** ([30d71ab](https://github.com/aaronvstory/email-management-tool/commit/30d71ab))
  - Automatic attachment file cleanup when emails are permanently deleted
  - Multi-layer security validations prevent path traversal attacks
  - Proper atomic operation order (DB DELETE → commit → file cleanup)
  - Comprehensive logging at debug, warning, info, and error levels
  - API returns file cleanup statistics (`files_deleted`, `files_failed`)
- **Metadata Verification** - Confirmed all attachment metadata fields populated correctly on upload
- **Documentation** ([ed25d26](https://github.com/aaronvstory/email-management-tool/commit/ed25d26))
  - Comprehensive Task 20 report (`.taskmaster/reports/task-20-attachment-storage-cleanup-complete.md`)
  - Updated TASK_PROGRESS.md with progress metrics (9/12 tasks, 47/65 subtasks)
  - Added shipping summary and test instructions

### Added - Task 19: Attachment UI Integration
- **Email List Indicators** ([4bb03ea](https://github.com/aaronvstory/email-management-tool/commit/4bb03ea), [ba08eb5](https://github.com/aaronvstory/email-management-tool/commit/ba08eb5))
  - Paperclip icon + count badge for emails with attachments
  - SQL query modified to include `attachment_count` via LEFT JOIN
  - Lime-themed styling matching project design
  - Conditional rendering (only when count > 0)
- **Email Detail Enhanced** (previous session)
  - Download All button for multiple attachments
  - File type icons using Material Symbols
  - Formatted file sizes (bytes/KB/MB)
  - MIME type display
  - Individual download buttons per attachment

### Added - Task 18: Attachment API
- **7 REST Endpoints** ([a76a212](https://github.com/aaronvstory/email-management-tool/commit/a76a212))
  - List attachments (`GET /api/email/<id>/attachments`)
  - Download by name (`GET /api/email/<id>/attachments/download/<filename>`)
  - Download by ID (`GET /api/attachment/<id>/download`)
  - **Download all as ZIP** (`GET /api/email/<id>/attachments/download-all`)
  - Upload attachment (`POST /api/email/<id>/attachments/upload`)
  - Mark attachment action (`POST /api/email/<id>/attachment/<aid>/mark`)
  - Delete staged attachment (`DELETE /api/email/<id>/attachment/<aid>/delete`)
- **Security Measures**
  - File size limits (25MB default)
  - MIME type whitelist validation
  - Path traversal prevention
  - Storage root validation
  - Version control (optimistic locking)

### Added - Task 17: Attachment Schema Migration
- **Database Schema** ([b6e243b](https://github.com/aaronvstory/email-management-tool/commit/b6e243b))
  - New `email_attachments` table with file-based storage
  - Metadata columns: `mime_type`, `size`, `sha256`, `storage_path`, `disposition`
  - Staging support: `is_original`, `is_staged` for edit workflow
  - Foreign key with `ON DELETE CASCADE` constraint
  - Index on `email_id` for query performance

### Fixed
- **Atomic Operations**: Database DELETE happens before file cleanup, preventing orphaned DB records
- **Path Security**: Multi-layer validation (_get_storage_roots, _is_under, resolve) prevents traversal
- **Error Handling**: Explicit rollback on exception, file deletion failures logged but don't block request

### Changed
- **Performance**: <5ms query overhead for attachment count in email list
- **Test Coverage**: Maintained at 34% (6611 statements)
- **Project Progress**: 75% tasks complete (9/12), 72.31% subtasks (47/65)

### Security
- **Path Validation**: Three-layer security check for all file operations
- **Transaction Safety**: Proper commit/rollback sequence prevents data loss
- **CSRF Protection**: Maintained across all new endpoints
- **Rate Limiting**: All endpoints protected

## [2.9.1] - 2025-10-25

### Added - Task 16: Accounts CSV Import
- CSV upload form with validation preview workflow
- Row-by-row validation with detailed error tracking
- Auto-detection of SMTP/IMAP settings using domain patterns
- INSERT vs UPDATE detection for existing accounts
- Helper functions for type conversion and normalization

### Added - Task 13: URL Consistency
- Converted all hardcoded routes to `url_for()`
- Standardized static asset references across 11 files
- All routes now use Blueprint endpoint names

### Added - Task 12: Stitch Migration
- 8 Stitch routes with dark theme and lime accents
- Interception test suite with 5-step flow visualization
- Diagnostics page with live log streaming
- Account management interface
- Watcher controls with real-time status

### Fixed
- Release/Discard buttons functional on both list and detail pages
- Attachment download returns 404 instead of 500 for missing files
- Dashboard badge alignment and styling
- IMAP watcher state persistence

## [2.9.0] - 2025-10-20

### Added
- Hybrid IMAP strategy (IDLE + polling fallback)
- Security hardening (CSRF, rate limiting, strong SECRET_KEY)
- Blueprint modularization (9 active blueprints)
- Comprehensive documentation (USER_GUIDE, API_REFERENCE, FAQ)
- UI tooltips across 3 templates

### Fixed
- Gmail authentication with App Password support
- IMAP timeout issues with hybrid polling
- Root directory cleanup (19 files organized)

---

## Project Information

**Repository**: https://github.com/aaronvstory/email-management-tool
**Documentation**: See `docs/` directory for comprehensive guides
**License**: MIT
**Python**: 3.9+ required
**Platform**: Windows (WSL compatible)

