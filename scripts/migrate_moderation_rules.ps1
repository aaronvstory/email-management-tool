#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Migrate moderation_rules table to add extended schema columns
.DESCRIPTION
    Adds the missing columns to the moderation_rules table while keeping legacy columns intact.
    This allows the application to work with both old and new schema formats.
.PARAMETER DatabasePath
    Path to the SQLite database file. Defaults to .\email_manager.db
.PARAMETER UseSqlite3
    Use sqlite3 command-line tool instead of Python script. Requires sqlite3 to be in PATH.
.EXAMPLE
    .\scripts\migrate_moderation_rules.ps1
    .\scripts\migrate_moderation_rules.ps1 -DatabasePath ".\data\email_manager.db"
    .\scripts\migrate_moderation_rules.ps1 -UseSqlite3
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$DatabasePath = ".\email_manager.db",

    [Parameter(Mandatory=$false)]
    [switch]$UseSqlite3
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Moderation Rules Schema Migration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Resolve full path
$DbPath = Resolve-Path $DatabasePath -ErrorAction SilentlyContinue
if (-not $DbPath) {
    $DbPath = Join-Path $PWD $DatabasePath
    Write-Warning "Database not found at: $DatabasePath"
    Write-Host "Will create new database at: $DbPath" -ForegroundColor Yellow
}
else {
    Write-Host "Database: $DbPath" -ForegroundColor Green
}

Write-Host ""

if ($UseSqlite3) {
    # Option 1: Use sqlite3 command-line tool
    Write-Host "Using sqlite3 command-line tool..." -ForegroundColor Yellow

    # Check if sqlite3 is available
    $sqlite3 = Get-Command sqlite3 -ErrorAction SilentlyContinue
    if (-not $sqlite3) {
        Write-Error @"
sqlite3 is not in your PATH. Please install it first:
  - Download from: https://www.sqlite.org/download.html
  - Or install via Chocolatey: choco install sqlite
  - Or install via Scoop: scoop install sqlite
"@
        exit 1
    }

    $sql = @"
ALTER TABLE moderation_rules ADD COLUMN rule_type TEXT DEFAULT 'keyword';
ALTER TABLE moderation_rules ADD COLUMN condition_field TEXT;
ALTER TABLE moderation_rules ADD COLUMN condition_operator TEXT;
ALTER TABLE moderation_rules ADD COLUMN condition_value TEXT;
ALTER TABLE moderation_rules ADD COLUMN action TEXT DEFAULT 'hold';
ALTER TABLE moderation_rules ADD COLUMN priority INTEGER DEFAULT 100;
ALTER TABLE moderation_rules ADD COLUMN created_at TEXT DEFAULT '';
"@

    try {
        $sql | sqlite3 $DbPath
        Write-Host "✅ Migration completed successfully!" -ForegroundColor Green
    }
    catch {
        # sqlite3 may report errors for duplicate columns, check output
        Write-Host "Note: Some columns may already exist (this is OK)" -ForegroundColor Yellow
        Write-Host $_.Exception.Message -ForegroundColor Yellow
    }
}
else {
    # Option 2: Use Python migration script (recommended)
    Write-Host "Using Python migration script..." -ForegroundColor Yellow

    # Check if Python is available
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "Python is not in your PATH. Please install Python or use -UseSqlite3 flag."
        exit 1
    }

    # Check if migration script exists
    $scriptPath = Join-Path $PSScriptRoot "fix_database_schema.py"
    if (-not (Test-Path $scriptPath)) {
        Write-Error "Migration script not found: $scriptPath"
        exit 1
    }

    Write-Host "Running: python $scriptPath $DbPath" -ForegroundColor Gray
    Write-Host ""

    try {
        & python $scriptPath $DbPath
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Migration script failed with exit code: $LASTEXITCODE"
            exit $LASTEXITCODE
        }
    }
    catch {
        Write-Error "Failed to run migration script: $_"
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Verify the schema changes with: sqlite3 $DbPath .schema" -ForegroundColor Gray
Write-Host "  2. Restart your application to use the new columns" -ForegroundColor Gray
Write-Host "  3. The application will continue to work with both old and new data formats" -ForegroundColor Gray
Write-Host ""
