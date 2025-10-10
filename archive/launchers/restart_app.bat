@echo off
echo Stopping old instances...
for /f "tokens=2" %%i in ('tasklist ^| findstr "python.exe"') do (
    tasklist /FI "PID eq %%i" /FI "WINDOWTITLE eq simple_app.py*" >nul 2>&1
    if not errorlevel 1 taskkill /F /PID %%i >nul 2>&1
)

echo Waiting for ports to be released...
timeout /t 3 /nobreak >nul

echo Starting application...
cd /d "%~dp0"
start /min cmd /c "python simple_app.py"

echo Waiting for initialization...
timeout /t 5 /nobreak >nul

echo Opening browser...
start http://localhost:5000

echo.
echo Application should be running at http://localhost:5000
echo Login: admin / admin123
pause