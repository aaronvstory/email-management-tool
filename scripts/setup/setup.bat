@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo    EMAIL MANAGEMENT TOOL - WINDOWS SETUP
echo ============================================================
echo.

:: Check Python installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo [OK] Python is installed
echo.

:: Create virtual environment
echo [2/6] Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists. Skipping...
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)
echo.

:: Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

:: Upgrade pip
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo [OK] Pip upgraded
echo.

:: Install requirements
echo [5/6] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

:: Create necessary directories
echo [6/6] Creating application directories...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "config" mkdir config
if not exist "config\certs" mkdir config\certs
echo [OK] Directories created
echo.

:: Create default config if not exists
if not exist "config\config.ini" (
    echo Creating default configuration...
    call :create_default_config
    echo [OK] Default configuration created
)

echo ============================================================
echo    SETUP COMPLETE!
echo ============================================================
echo.
echo Next steps:
echo 1. Edit config\config.ini with your email settings
echo 2. Run 'start.bat' to launch the application
echo 3. Access dashboard at http://localhost:5000
echo    Default login: admin / admin123
echo.
pause
exit /b 0

:create_default_config
(
echo [SMTP_PROXY]
echo host = 0.0.0.0
echo port = 8587
echo max_message_size = 33554432
echo.
echo [SMTP_RELAY]
echo # Configure your SMTP server for sending approved emails
echo relay_host = smtp.gmail.com
echo relay_port = 587
echo use_tls = true
echo # Add your credentials here
echo username = 
echo password = 
echo.
echo [WEB_INTERFACE]
echo host = 127.0.0.1
echo port = 5000
echo secret_key = %RANDOM%%RANDOM%%RANDOM%%RANDOM%
echo debug = false
echo.
echo [DATABASE]
echo database_path = data/email_moderation.db
echo.
echo [SECURITY]
echo # Session timeout in minutes
echo session_timeout = 30
echo # Max login attempts before lockout
echo max_login_attempts = 5
echo # Lockout duration in minutes
echo lockout_duration = 15
echo.
echo [LOGGING]
echo log_level = INFO
echo log_file = logs/email_moderation.log
echo max_log_size = 10485760
echo backup_count = 5
) > config\config.ini
exit /b 0