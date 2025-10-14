@echo off
echo ========================================
echo Email Management Tool UI Testing
echo ========================================
echo.

REM Check if Playwright is installed
python -c "import playwright" 2>nul
if errorlevel 1 (
    echo Installing Playwright...
    pip install playwright
    python -m playwright install chromium
)

REM Run the test
echo Starting UI test suite...
python start_and_test.py

echo.
echo Test completed!
pause