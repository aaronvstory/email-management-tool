#!/usr/bin/env bash
# ============================================================
#    EMAIL MANAGEMENT TOOL - QUICK LAUNCHER (macOS / Linux / WSL)
# ============================================================
#    One-click launcher that starts the app and opens browser
#    Now cross-platform: macOS, Linux, and WSL on Windows
# ============================================================

clear

echo ""
echo "============================================================"
echo "   EMAIL MANAGEMENT TOOL - PROFESSIONAL LAUNCHER"
echo "============================================================"
echo ""

# --- helpers -------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

open_url() {
    local url="$1"
    # Prefer platform-specific options
    if have wslview; then
        # WSL-friendly browser opener
        wslview "$url" >/dev/null 2>&1 &
        return 0
    fi
    if have xdg-open; then
        xdg-open "$url" >/dev/null 2>&1 &
        return 0
    fi
    if have powershell.exe; then
        powershell.exe -NoProfile -Command "Start-Process '$url'" >/dev/null 2>&1 &
        return 0
    fi
    if have open; then
        open "$url" >/dev/null 2>&1 &
        return 0
    fi
    echo "[INFO] Open your browser to: $url"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in PATH!"
    echo "Please install Python 3.8 or higher."
    read -p "Press Enter to exit..."
    exit 1
fi

# Check for port conflicts and clean up if needed
echo "[PREFLIGHT] Checking for port conflicts..."

# Check port 5000 (Flask)
if (have lsof && lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1) || \
   (! have lsof && netstat -tuln 2>/dev/null | grep -q ":5000 "); then
    echo "[WARNING] Port 5000 is in use. Checking if it's our application..."

    # Try to access health endpoint
    if curl -s http://localhost:5000/healthz >/dev/null 2>&1; then
        echo "[INFO] Application is already running and healthy!"
        echo ""
        echo "Opening dashboard in browser..."
        sleep 2
        open_url http://localhost:5000
        echo ""
        echo "[OK] Browser launched!"
        sleep 3
        exit 0
    else
        echo "[WARNING] Port 5000 occupied by unresponsive process."
        echo "[ACTION] Attempting safe cleanup..."

        # Kill only our Python processes running simple_app.py
        if have lsof; then
            for pid in $(lsof -ti :5000); do
                if ps -p $pid -o command= | grep -q "simple_app.py"; then
                    kill -9 $pid 2>/dev/null
                fi
            done
        else
            # Best-effort fallback: attempt to kill python using port 5000
            if have fuser; then
                fuser -k 5000/tcp 2>/dev/null || true
            fi
        fi
        sleep 2
    fi
fi

# Check port 8587 (SMTP Proxy)
if (have lsof && lsof -Pi :8587 -sTCP:LISTEN -t >/dev/null 2>&1) || \
   (! have lsof && netstat -tuln 2>/dev/null | grep -q ":8587 "); then
    echo "[WARNING] Port 8587 is in use. Attempting safe cleanup..."
    if have lsof; then
        for pid in $(lsof -ti :8587); do
            if ps -p $pid -o command= | grep -q "simple_app.py"; then
                kill -9 $pid 2>/dev/null
            fi
        done
    else
        if have fuser; then
            fuser -k 8587/tcp 2>/dev/null || true
        fi
    fi
    sleep 2
fi

echo "[OK] Ports are clear!"

echo "[STARTING] Email Management Tool..."
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    # Legacy venv folder
    source venv/bin/activate
elif [ -d ".venv" ]; then
    # Common name used by uv/venv
    source .venv/bin/activate
fi

# Start the Flask application in background
echo "[1/3] Starting Flask application..."
nohup python3 simple_app.py > /dev/null 2>&1 &

# Wait for application to initialize
echo "[2/3] Waiting for services to initialize..."
sleep 5

# Check if app started successfully
if ! lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo ""
    echo "[ERROR] Failed to start application!"
    echo "Please check if port 5000 is available."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[3/3] Opening dashboard in browser..."
echo ""

# Open the dashboard in default browser
open_url http://localhost:5000

echo "============================================================"
echo "   APPLICATION STARTED SUCCESSFULLY!"
echo "============================================================"
echo ""
echo "   Web Dashboard:  http://localhost:5000"
echo "   SMTP Proxy:     localhost:8587"
echo "   Login:          admin / admin123"
echo ""
echo "   The dashboard has been opened in your browser."
echo "   This script will exit, but the app continues running."
echo ""
echo "   To stop: Run ./email_manager.sh and select 'Stop Application'"
echo "============================================================"
echo ""

read -p "Press Enter to exit..."
