@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo    EMAIL MANAGEMENT TOOL - LAUNCHER
echo ============================================================
echo.

:: Check if virtual environment exists
if not exist ".venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup-uv.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

:: Check if dependencies are installed
python -c "import flask, sqlalchemy, aiosmtpd" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Dependencies not installed!
    echo Please run setup-uv.bat first.
    pause
    exit /b 1
)

:: Clear screen for clean display
cls

echo ============================================================
echo    EMAIL MANAGEMENT TOOL - STARTING SERVICES
echo ============================================================
echo.
echo [*] Starting Email Management Tool...
echo [*] SMTP Proxy Port: 8587
echo [*] Web Dashboard: http://localhost:5000
echo [*] Default Login: admin / admin123
echo.
echo [*] Press Ctrl+C to stop the application
echo.
echo ============================================================
echo.

:: Start the application
python simple_app.py

:: If we get here, the app has stopped
echo.
echo Application stopped.
pause
exit /b 0