@echo off
REM ============================================================
REM    EMAIL MANAGEMENT TOOL - RESTART SCRIPT
REM ============================================================

cls
echo.
echo ============================================================
echo    RESTARTING EMAIL MANAGEMENT TOOL
echo ============================================================
echo.

echo [1/3] Stopping existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8587') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [2/3] Waiting for cleanup...
timeout /t 3 /nobreak >nul

echo [3/3] Starting application...
start /min cmd /c "python simple_app.py"

echo.
echo Waiting for application to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo    APPLICATION RESTARTED!
echo ============================================================
echo.
echo    Web Dashboard:  http://localhost:5000/emails-unified
echo    Login:          admin / admin123
echo.
echo Opening dashboard in browser...
start http://localhost:5000/emails-unified

echo.
echo Done! Press any key to exit...
pause >nul