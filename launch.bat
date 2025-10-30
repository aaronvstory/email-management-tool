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

REM Configurable Flask port (default 5000) for cleanup and readiness
set PORT=5000
if defined LAUNCHER_PORT set PORT=%LAUNCHER_PORT%

REM ALWAYS kill old processes - force clean start every time
echo [CLEANUP] Killing old Flask processes...

REM Method 1: Kill all python processes running simple_app.py
for /f "tokens=2" %%a in ('tasklist ^| findstr /I "python.exe"') do (
    REM Check if this python is running simple_app.py
    tasklist /FI "PID eq %%a" /V 2>nul | findstr /I "simple_app.py" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [KILL] Terminating old Flask process (PID %%a)
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM Method 2: Kill anything on our ports (web + SMTP proxy)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% :8587"') do (
    REM Skip if not a PID (header lines)
    echo %%a | findstr /R "^[0-9][0-9]*$" >nul
    if !ERRORLEVEL! EQU 0 (
        echo [KILL] Clearing port conflict (PID %%a)
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM Wait a moment for ports to fully release
timeout /t 1 /nobreak >nul

echo [OK] All old processes terminated!
echo [STARTING] Email Management Tool...
echo.

REM Resolve Python interpreter (prefer local venv)
echo [1/3] Starting Flask application...
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" (
    echo [PYTHON] Using virtual environment: %PYTHON_EXE%
) else (
    set "PYTHON_EXE=python"
    echo [PYTHON] Using system Python from PATH
)

REM If caller sets LAUNCHER_PORT, pass it into FLASK_PORT for the app
if defined LAUNCHER_PORT set FLASK_PORT=%LAUNCHER_PORT%

REM Ensure logs directory exists
if not exist "%CD%\logs" mkdir "%CD%\logs" >nul 2>&1

REM Launch app minimized (simple and reliable) with stdout/err to logs
start "EMT-App" /min cmd /c ""%PYTHON_EXE%" "%CD%\simple_app.py" 1>>"%CD%\logs\app.out" 2>>"%CD%\logs\app.err""
echo [PID] Launched app (lookup by script name)

REM Smart wait - poll for ready state instead of fixed delay
echo [2/3] Waiting for services to initialize...
set MAX_RETRIES=45
REM Allow override via environment variable LAUNCHER_MAX_WAIT (in seconds)
if defined LAUNCHER_MAX_WAIT set MAX_RETRIES=%LAUNCHER_MAX_WAIT%
set RETRY_COUNT=0

REM Allow configurable Flask port (default 5000)
set PORT=5000
if defined LAUNCHER_PORT set PORT=%LAUNCHER_PORT%

:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a RETRY_COUNT+=1

REM Early-exit if the app process crashed (no simple_app.py found in task list)
if %RETRY_COUNT% GTR 2 (
    tasklist /V | findstr /I "simple_app.py" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
    echo(
    echo [ERROR] Application process exited early.
    echo        Check console output or logs if available.
    echo(
    pause
    exit /b 1
    )
)

REM Check if app is listening on configured port
netstat -an | findstr :%PORT% | findstr LISTENING >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Port is open, now check lightweight readiness endpoint using PowerShell
    powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:%PORT%/readyz; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Application is ready!
        goto APP_READY
    ) else (
        REM Fallback: try full healthz (may be 503 early during warm-up)
        powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:%PORT%/healthz; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            echo [OK] Application health passed!
            goto APP_READY
        )
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

REM Generate cache-busting timestamp
set TIMESTAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Open with cache-busting parameter to force reload
echo [CACHE] Forcing browser cache refresh with timestamp: %TIMESTAMP%
start http://127.0.0.1:%PORT%/?v=%TIMESTAMP%

echo ============================================================
echo    APPLICATION STARTED SUCCESSFULLY!
echo ============================================================
echo.
echo    Web Dashboard:  http://127.0.0.1:%PORT%
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
