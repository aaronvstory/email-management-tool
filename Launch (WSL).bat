@echo off
REM ============================================================
REM   Email Management Tool - WSL Launcher (Double-click me)
REM ============================================================

setlocal
REM Change this to your project path in WSL if different
set "WSL_PROJECT_DIR=/home/d0nbx/email-management-tool"

REM Prefer Windows Terminal if available for a nicer experience
where wt.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM New tab running the launcher inside default WSL distro
    wt.exe -w 0 nt --title "Email Tool" wsl.exe -e bash -lc "cd '%WSL_PROJECT_DIR%' && chmod +x launch.sh 2>/dev/null || true; ./launch.sh"
    goto :eof
)

REM Fallback to plain console
wsl.exe -e bash -lc "cd '%WSL_PROJECT_DIR%' && chmod +x launch.sh 2>/dev/null || true; ./launch.sh"

REM If the launcher returns immediately, keep the window open
pause
