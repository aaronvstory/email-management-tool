@echo off
REM Simple one-command launcher: boot → snap → open
echo ============================================================
echo    Email Manager - Boot + Screenshot + Open
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File ".\manage.ps1" boot-snap-open -BaseUrl http://localhost:5000
