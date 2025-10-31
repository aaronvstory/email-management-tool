@echo off
REM Migrate moderation_rules table schema
REM Adds extended columns while keeping legacy columns intact

echo ========================================
echo Moderation Rules Schema Migration
echo ========================================
echo.

if "%1"=="" (
    set DB_PATH=.\email_manager.db
) else (
    set DB_PATH=%1
)

echo Database: %DB_PATH%
echo.

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not in your PATH
    echo Please install Python or use the PowerShell script with -UseSqlite3 flag
    exit /b 1
)

REM Run the migration script
python scripts\fix_database_schema.py "%DB_PATH%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Migration Complete!
    echo ========================================
    echo.
    echo Next steps:
    echo   1. Restart your application
    echo   2. The app will work with both old and new data formats
    echo.
) else (
    echo.
    echo Migration failed with error code: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
