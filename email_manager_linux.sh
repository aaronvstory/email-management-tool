#!/bin/bash
# ============================================================
#    EMAIL MANAGEMENT TOOL - MENU LAUNCHER (Linux)
# ============================================================
#    Professional launcher with menu options
# ============================================================

show_menu() {
    clear

    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo ""
    echo "                         EMAIL MANAGEMENT TOOL (Linux)"
    echo "                    Interception and Moderation System"
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    # Check if app is running
    if ss -tuln | grep -q ':5000 '; then
        echo "   STATUS: [RUNNING] Application is active on port 5000"
        APP_STATUS="RUNNING"
    else
        echo "   STATUS: [STOPPED] Application is not running"
        APP_STATUS="STOPPED"
    fi

    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   MAIN MENU"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""
    echo "   [1] Start Application and Open Dashboard"
    echo "   [2] Open Dashboard Only (if already running)"
    echo "   [3] Stop Application"
    echo "   [4] Check Status"
    echo "   [5] View Logs"
    echo "   [6] Test Email Connections"
    echo "   [7] Clean Temporary Files"
    echo "   [Q] Quit"
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    read -p "   Enter your choice: " CHOICE

    case "$CHOICE" in
        1) start_app ;;
        2) open_browser ;;
        3) stop_app ;;
        4) check_status ;;
        5) view_logs ;;
        6) test_connections ;;
        7) clean_temp ;;
        q|Q) exit_menu ;;
        *)
            echo ""
            echo "   [ERROR] Invalid choice! Please try again."
            sleep 2
            show_menu
            ;;
    esac
}

start_app() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   STARTING EMAIL MANAGEMENT TOOL"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    if [ "$APP_STATUS" = "RUNNING" ]; then
        echo "   [WARN] Application is already running!"
        echo ""
        echo "   Opening dashboard in browser..."
        xdg-open http://localhost:5000 2>/dev/null || sensible-browser http://localhost:5000 2>/dev/null || echo "   [ERROR] Could not open browser automatically"
        echo "   [OK] Dashboard opened!"
        sleep 3
        show_menu
        return
    fi

    echo "   [1/5] Checking Python installation..."
    if ! command -v python3 &> /dev/null; then
        echo "   [ERROR] Python 3 is not installed!"
        read -p "   Press Enter to continue..."
        show_menu
        return
    fi
    echo "   [OK] Python 3 found"

    echo "   [2/5] Activating virtual environment..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo "   [OK] Virtual environment activated"
    else
        echo "   [WARN] No virtual environment found, using system Python"
    fi

    echo "   [3/5] Starting Flask application..."
    nohup python3 simple_app.py > /dev/null 2>&1 &
    echo $! > .app.pid

    echo "   [4/5] Waiting for services to initialize..."
    sleep 5

    echo "   [5/5] Opening dashboard in browser..."
    xdg-open http://localhost:5000 2>/dev/null || sensible-browser http://localhost:5000 2>/dev/null || echo "   [INFO] Please open http://localhost:5000 in your browser"

    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   [SUCCESS] Application started successfully!"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""
    echo "   Web Dashboard:  http://localhost:5000"
    echo "   SMTP Proxy:     localhost:8587"
    echo "   Login:          admin / admin123"
    echo ""
    read -p "   Press Enter to return to menu..."
    show_menu
}

open_browser() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   OPENING DASHBOARD"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""
    xdg-open http://localhost:5000 2>/dev/null || sensible-browser http://localhost:5000 2>/dev/null || echo "   [ERROR] Could not open browser automatically"
    echo "   [OK] Dashboard opened in default browser!"
    echo ""
    echo "   Login Credentials:"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo ""
    read -p "   Press Enter to return to menu..."
    show_menu
}

stop_app() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   STOPPING APPLICATION"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    if [ "$APP_STATUS" = "STOPPED" ]; then
        echo "   [INFO] Application is not running."
        sleep 2
        show_menu
        return
    fi

    echo "   Stopping Python processes..."

    # Kill using PID file if available
    if [ -f ".app.pid" ]; then
        PID=$(cat .app.pid)
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID 2>/dev/null
            echo "   Killed PID $PID (from .app.pid)"
        fi
        rm -f .app.pid
    fi

    # Kill processes on port 5000 (Flask)
    for pid in $(ss -tulpn 2>/dev/null | grep ':5000' | grep -oP 'pid=\K[0-9]+'); do
        if ps -p $pid -o command= 2>/dev/null | grep -q "simple_app.py"; then
            kill -9 $pid 2>/dev/null
            echo "   Killed PID $pid (Flask)"
        fi
    done

    # Fallback: kill all python processes running simple_app.py
    pkill -f "python3.*simple_app.py" 2>/dev/null

    echo "   [OK] Application stopped successfully!"
    echo ""
    read -p "   Press Enter to return to menu..."
    show_menu
}

check_status() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   SYSTEM STATUS"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    # Check Flask app
    if ss -tuln 2>/dev/null | grep -q ':5000 '; then
        echo "   [OK]    Web Dashboard:    RUNNING on port 5000"
    else
        echo "   [WARN]  Web Dashboard:    NOT RUNNING"
    fi

    # Check SMTP proxy
    if ss -tuln 2>/dev/null | grep -q ':8587 '; then
        echo "   [OK]    SMTP Proxy:       LISTENING on port 8587"
    else
        echo "   [WARN]  SMTP Proxy:       NOT LISTENING"
    fi

    # Check database
    if [ -f "email_manager.db" ]; then
        SIZE=$(stat -c%s email_manager.db 2>/dev/null || echo "unknown")
        echo "   [OK]    Database:         Found (Size: $SIZE bytes)"
    else
        echo "   [WARN]  Database:         NOT FOUND"
    fi

    # Check Python
    if command -v python3 &> /dev/null; then
        VERSION=$(python3 --version)
        echo "   [OK]    Python:           INSTALLED ($VERSION)"
    else
        echo "   [ERROR] Python:           NOT FOUND"
    fi

    # Check virtual environment
    if [ -d "venv" ]; then
        echo "   [OK]    Virtual Env:      FOUND"
    else
        echo "   [WARN]  Virtual Env:      NOT FOUND"
    fi

    echo ""
    read -p "   Press Enter to return to menu..."
    show_menu
}

view_logs() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   APPLICATION LOGS"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    if [ -f "logs/app.log" ]; then
        echo "   Last 20 lines of logs/app.log:"
        echo "   -------------------------"
        tail -20 logs/app.log
    elif [ -f "app.log" ]; then
        echo "   Last 20 lines of app.log:"
        echo "   -------------------------"
        tail -20 app.log
    else
        echo "   [INFO] No log file found."
    fi

    echo ""
    read -p "   Press Enter to return to menu..."
    show_menu
}

test_connections() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   TESTING EMAIL CONNECTIONS"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    if [ -f "scripts/test_all_connections.py" ]; then
        python3 scripts/test_all_connections.py
    elif [ -f "scripts/test_permanent_accounts.py" ]; then
        python3 scripts/test_permanent_accounts.py
    else
        echo "   [ERROR] Test script not found!"
        echo "   Looking for: scripts/test_all_connections.py"
    fi

    echo ""
    read -p "   Press Enter to return to menu..."
    show_menu
}

clean_temp() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   CLEANING TEMPORARY FILES"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""

    echo "   Removing Python cache..."
    if [ -d "__pycache__" ]; then
        rm -rf __pycache__
        echo "   [OK] __pycache__ removed"
    fi

    echo "   Cleaning .pyc files..."
    find . -name "*.pyc" -delete 2>/dev/null
    echo "   [OK] .pyc files cleaned"

    echo "   Removing temporary test files..."
    rm -f test_*.json workflow_test_*.json 2>/dev/null
    echo "   [OK] Temporary test files cleaned"

    echo ""
    echo "   [SUCCESS] Cleanup complete!"
    echo ""
    read -p "   Press Enter to return to menu..."
    show_menu
}

exit_menu() {
    clear
    echo ""
    echo "   -----------------------------------------------------------------------------------------"
    echo "   Thank you for using Email Management Tool!"
    echo "   -----------------------------------------------------------------------------------------"
    echo ""
    sleep 2
    exit 0
}

# Main entry point
show_menu
