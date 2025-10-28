@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM    EMAIL MANAGEMENT TOOL - QUICK LAUNCHER
REM ============================================================
REM    One-click launcher that starts the app and opens browser
REM ============================================================

cls
color 0A

echo.
echo ============================================================
echo    EMAIL MANAGEMENT TOOL - PROFESSIONAL LAUNCHER
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check for port conflicts and clean up if needed
echo [PREFLIGHT] Checking for port conflicts...

REM Quick health check first - if app is running and healthy, just launch browser
curl -s --max-time 2 http://127.0.0.1:5000/healthz >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Application is already running and healthy!
    echo [OK] Opening dashboard in browser...
    start http://127.0.0.1:5000
    timeout /t 2 /nobreak >nul
    exit /b 0
)

REM Get all PIDs on our ports in one netstat call (much faster)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 :8587"') do (
    REM Skip if not a PID (header lines)
    echo %%a | findstr /R "^[0-9][0-9]*$" >nul
    if !ERRORLEVEL! EQU 0 (
        REM Kill without checking commandline (faster, safer than WMIC)
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [OK] Ports cleared!
echo [STARTING] Email Management Tool...
echo.

REM Start the Flask application in background
echo [1/3] Starting Flask application...
start /min cmd /c "python simple_app.py"

REM Smart wait - poll for ready state instead of fixed delay
echo [2/3] Waiting for services to initialize...
set MAX_RETRIES=15
set RETRY_COUNT=0

:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a RETRY_COUNT+=1

REM Check if app is listening on port 5000
netstat -an | findstr :5000 | findstr LISTENING >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Port is open, now check health endpoint
    curl -s --max-time 2 http://127.0.0.1:5000/healthz >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Application is healthy!
        goto APP_READY
    )
)

if %RETRY_COUNT% LSS %MAX_RETRIES% goto WAIT_LOOP

echo.
echo [ERROR] Failed to start application after %MAX_RETRIES% seconds!
echo Please check logs/app.log for errors.
pause
exit /b 1

:APP_READY
echo [3/3] Opening dashboard in browser...
echo.

REM Open the dashboard in default browser
start http://127.0.0.1:5000

echo ============================================================
echo    APPLICATION STARTED SUCCESSFULLY!
echo ============================================================
echo.
echo    Web Dashboard:  http://127.0.0.1:5000
echo    SMTP Proxy:     localhost:8587
echo    Login:          admin / admin123
echo.
echo    Dashboard opened in browser (took %RETRY_COUNT% seconds)
echo    Keep this window open while using the application.
echo.
echo    Press any key to stop the application...
echo ============================================================
echo.

REM Keep window open to show status
pause >nul
