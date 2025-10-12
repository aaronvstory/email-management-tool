@echo off
echo.
echo ====================================================================
echo   Gmail SMTP Firewall Fix for Email Manager
echo ====================================================================
echo.
echo This script will add Windows Firewall rules to allow Gmail SMTP.
echo You need to run this as Administrator.
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo.
    echo Right-click on this file and select "Run as administrator"
    pause
    exit /b 1
)

echo [INFO] Adding firewall rules for Gmail SMTP...
echo.

:: Add outbound rules for Gmail SMTP
echo Adding rule for SMTP port 587 (STARTTLS)...
netsh advfirewall firewall add rule name="Email Manager - Gmail SMTP 587" dir=out action=allow protocol=TCP remoteport=587

echo Adding rule for SMTP port 465 (SSL)...
netsh advfirewall firewall add rule name="Email Manager - Gmail SMTP 465" dir=out action=allow protocol=TCP remoteport=465

echo Adding rule for SMTP port 25 (Standard)...
netsh advfirewall firewall add rule name="Email Manager - Gmail SMTP 25" dir=out action=allow protocol=TCP remoteport=25

echo.
echo [INFO] Firewall rules added successfully!
echo.
echo ====================================================================
echo   Testing connectivity to Gmail SMTP...
echo ====================================================================
echo.

powershell -Command "Test-NetConnection -ComputerName smtp.gmail.com -Port 587"

echo.
echo ====================================================================
echo   DONE! You can now try sending emails again.
echo ====================================================================
echo.
pause