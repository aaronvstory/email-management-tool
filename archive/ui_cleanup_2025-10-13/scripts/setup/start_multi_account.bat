@echo off
cls
echo ========================================================================
echo                  ENHANCED EMAIL MANAGEMENT TOOL
echo                     WITH MULTI-ACCOUNT SUPPORT
echo ========================================================================
echo.
echo Starting comprehensive email management system...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    pause
    exit /b 1
)

REM Check required packages
echo Checking required packages...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install flask flask-login python-dotenv aiosmtpd cryptography requests
)

REM Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist ".claude" mkdir .claude
if not exist ".claude\research" mkdir .claude\research

REM Start the multi-account application
echo.
echo ========================================================================echo Starting Email Management Tool...
echo ========================================================================
echo.
echo Features:
echo   - Multi-Account Support (Gmail, Hostinger, Outlook, Custom)
echo   - Email Interception and Moderation
echo   - Risk Scoring and Classification
echo   - Account Import/Export
echo   - Comprehensive Diagnostics
echo   - Real-time Dashboard
echo.
echo Access Points:
echo   - Web Dashboard: http://localhost:5000
echo   - SMTP Proxy: localhost:8587
echo   - Default Login: admin / admin123
echo.
echo Configured Accounts:
echo   1. Hostinger - mcintyre@corrinbox.com
echo   2. Gmail - ndayijecika@gmail.com
echo.
echo ========================================================================
echo.

REM Start the application
python multi_account_app.py

if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start
    echo Check the error messages above for details
    pause
)

pause