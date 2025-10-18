#!/bin/bash
# Keep-alive script for Codex container

# This script prevents the container from exiting by running a persistent process
# It also sets up the environment and provides an interactive shell

echo "================================================"
echo "  Initializing Email Management Tool Container"
echo "================================================"

# Set up environment
export TERM=xterm-256color
export SHELL=/bin/bash
export PS1='\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
export FLASK_APP=simple_app.py
export FLASK_ENV=development
export PYTHONPATH=/workspace:$PYTHONPATH
export DEBIAN_FRONTEND=noninteractive

# Change to workspace directory
cd /workspace 2>/dev/null || cd /

# Install minimal requirements if missing
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing core dependencies..."
    pip install flask aiosmtpd cryptography bcrypt 2>/dev/null || true
fi

# Create necessary files and directories
mkdir -p app templates static scripts tests logs archive 2>/dev/null
touch app.log 2>/dev/null

# Generate encryption key if needed
if [ ! -f key.txt ]; then
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > key.txt 2>/dev/null || true
fi

# Create a minimal Flask app if simple_app.py doesn't exist
if [ ! -f simple_app.py ]; then
    cat > simple_app.py << 'PYEOF'
#!/usr/bin/env python3
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Email Management Tool - Container is running!"

if __name__ == '__main__':
    print("Starting Flask app on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
PYEOF
fi

echo ""
echo "================================================"
echo "  Container Ready and Running!"
echo "================================================"
echo ""
echo "Python: $(python3 --version 2>&1)"
echo "Working directory: $(pwd)"
echo ""
echo "Available commands:"
echo "  python simple_app.py  - Start the Flask application"
echo "  pytest tests/         - Run tests"
echo "  exit                  - Exit the container"
echo ""
echo "================================================"

# Keep the container alive with an interactive bash session
# This is the critical part - we use exec to replace the current shell
# with bash, preventing the container from exiting
exec /bin/bash --login