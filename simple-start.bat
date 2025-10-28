@echo off
echo ============================================================
echo    SIMPLE LAUNCHER - AUTO-NAVIGATE
echo ============================================================

REM Change to project directory
cd /d "C:\claude\Email-Management-Tool"

REM Check if we're in the right place now
if not exist "simple_app.py" (
    echo ERROR: Could not find C:\claude\Email-Management-Tool\simple_app.py
    echo Make sure the project exists in that location.
    pause
    exit
)

echo Found project! Starting Flask...

REM Kill old processes
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting Flask server...
start "Flask Server" cmd /k "python simple_app.py"

echo Waiting for server...
timeout /t 8 /nobreak >nul

echo Opening browser...
set timestamp=%random%%random%
start http://127.0.0.1:5000/?v=%timestamp%

echo Done! Check the Flask Server window for any errors.
pause
