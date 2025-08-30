@echo off
:: Email Management Tool - Test Runner
:: Launches PowerShell test suite with proper environment

echo ============================================================
echo    EMAIL MANAGEMENT TOOL - COMPREHENSIVE TEST SUITE
echo ============================================================
echo.
echo Starting test execution...
echo.

:: Check if PowerShell is available
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell is not available on this system
    pause
    exit /b 1
)

:: Launch PowerShell test runner
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0test-runner.ps1" %*

:: Capture exit code
set EXIT_CODE=%errorlevel%

:: Display result
echo.
if %EXIT_CODE% equ 0 (
    echo ============================================================
    echo    ALL TESTS PASSED SUCCESSFULLY!
    echo ============================================================
) else (
    echo ============================================================
    echo    TESTS FAILED - Check output above for details
    echo ============================================================
)

echo.
pause
exit /b %EXIT_CODE%