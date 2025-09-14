@echo off
REM ========================================================
REM    EMAIL MANAGEMENT TOOL - LAUNCHER
REM ========================================================
REM    Quick launcher for Email Management Tool
REM    Runs PowerShell script with proper execution policy
REM ========================================================

cls
echo.
echo ========================================================
echo    EMAIL MANAGEMENT TOOL - STARTING...
echo ========================================================
echo.

REM Check if PowerShell script exists
if not exist "%~dp0manage.ps1" (
    echo ERROR: manage.ps1 not found!
    echo Please ensure manage.ps1 is in the same directory as this batch file.
    pause
    exit /b 1
)

REM Launch PowerShell script with bypass execution policy
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0manage.ps1" start

REM Check if PowerShell script executed successfully
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================================
    echo    ERROR: Failed to start Email Management Tool
    echo ========================================================
    pause
    exit /b %ERRORLEVEL%
)

exit /b 0