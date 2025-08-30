@echo off
:: Email Management Tool - UV Setup Launcher
:: This batch file launches the PowerShell setup script with proper execution policy

echo ============================================================
echo    EMAIL MANAGEMENT TOOL - UV SETUP
echo ============================================================
echo.
echo Starting advanced setup with UV package manager...
echo.

:: Check if PowerShell is available
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell is not available on this system
    echo Please ensure Windows PowerShell is installed
    pause
    exit /b 1
)

:: Launch PowerShell setup script with bypass execution policy
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-uv.ps1"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Setup failed. Please check the error messages above.
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo    SETUP COMPLETE!
echo ============================================================
echo.
echo Next steps:
echo 1. Run 'start-app.bat' to launch the application
echo 2. Run 'test-all.bat' to execute complete test suite
echo 3. Access dashboard at http://localhost:5000
echo.
pause