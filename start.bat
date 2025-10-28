@echo off
REM Compatibility launcher — delegates to the current main launcher
SETLOCAL
CALL "%~dp0launch.bat"
ENDLOCAL
