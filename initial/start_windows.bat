@echo off
echo ========================================
echo Email Moderation System - Windows Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python is installed ✓

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q aiosmtpd flask flask-sqlalchemy email-validator dkimpy cryptography dnspython python-dateutil werkzeug jinja2 requests

REM Create directories if they don't exist
if not exist "logs" mkdir logs
if not exist "data" mkdir data

echo.
echo ========================================
echo Starting Email Moderation System...
echo ========================================
echo.
echo 📧 SMTP Proxy will start on port 8587
echo 🌐 Web Dashboard: http://127.0.0.1:5000
echo.
echo Configure your email client:
echo   SMTP Server: 127.0.0.1
echo   SMTP Port: 8587
echo   Security: None (for testing)
echo.
echo Press Ctrl+C to stop the system
echo ========================================
echo.

REM Start the application
python main.py

pause
