#!/bin/bash
# Startup script for Codex container - ensures terminal stays connected

# Prevent the container from exiting immediately
trap '' TERM INT

# Set up the environment
export TERM=xterm-256color
export SHELL=/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export FLASK_APP=simple_app.py
export FLASK_ENV=development
export PYTHONPATH=/workspace:$PYTHONPATH

# Ensure bash is available
if [ ! -x /bin/bash ]; then
    echo "Installing bash..."
    apt-get update && apt-get install -y bash
fi

# Copy bashrc if it exists
if [ -f /workspace/.bashrc ]; then
    cp /workspace/.bashrc ~/.bashrc
    source ~/.bashrc
fi

# Change to workspace
cd /workspace 2>/dev/null || cd /

# Quick dependency check
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found, installing..."
    apt-get update && apt-get install -y python3 python3-pip
fi

# Install minimal Flask if missing
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing Flask..."
    pip3 install flask 2>/dev/null || pip install flask 2>/dev/null
fi

# Create directories
mkdir -p app templates static scripts tests 2>/dev/null

# Show status
echo ""
echo "Email Management Tool Container - Ready"
echo "========================================="
echo "Python: $(python3 --version 2>&1 || python --version 2>&1)"
echo "Working dir: $(pwd)"
echo "Terminal: Connected"
echo ""

# CRITICAL: Start an interactive bash shell that won't exit
# Using exec replaces this script process with bash, keeping the container alive
exec /bin/bash --login -i