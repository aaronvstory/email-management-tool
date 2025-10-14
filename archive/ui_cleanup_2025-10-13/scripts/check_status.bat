@echo off
echo ================================================================================
echo EMAIL MANAGEMENT TOOL - STATUS CHECK
echo ================================================================================
echo.

echo [1/4] Checking Python processes...
tasklist | findstr python.exe
echo.

echo [2/4] Checking port 5000 (Flask)...
netstat -an | findstr ":5000"
echo.

echo [3/4] Checking port 8587 (SMTP Proxy)...
netstat -an | findstr ":8587"
echo.

echo [4/4] Testing HTTP endpoint...
curl -s -o nul -w "HTTP Response: %%{http_code}\n" http://localhost:5000/ 2>nul || echo Connection failed
echo.

echo ================================================================================
echo STATUS CHECK COMPLETE
echo ================================================================================
echo.
echo To access the app:
echo   1. Open browser: http://localhost:5000
echo   2. Login: admin / admin123
echo   3. Navigate to Accounts to see permanent test accounts
echo.
pause
