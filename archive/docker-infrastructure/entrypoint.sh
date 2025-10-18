#!/bin/bash
# Custom entrypoint script to keep Codex container alive

echo "================================================"
echo "  Starting Email Management Tool Container"
echo "================================================"

# Set environment variables
export TERM=xterm-256color
export SHELL=/bin/bash
export PS1='\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
export FLASK_APP=simple_app.py
export FLASK_ENV=development
export PYTHONPATH=/workspace:$PYTHONPATH

# Navigate to workspace
cd /workspace 2>/dev/null || cd /

# Install dependencies if not already installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing Python dependencies..."
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt 2>/dev/null || \
        pip install flask flask-login flask-wtf aiosmtpd cryptography bcrypt 2>/dev/null
    fi
fi

# Create necessary directories
mkdir -p app templates static scripts tests logs archive 2>/dev/null

# Generate encryption key if needed
if [ ! -f key.txt ]; then
    echo "Generating encryption key..."
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > key.txt 2>/dev/null || true
fi

# Create .env from example if needed
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
fi

# Create a proper bashrc
cat > ~/.bashrc << 'EOF'
#!/bin/bash
export PS1='\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
alias ll='ls -alF --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias python='python3'
alias pip='pip3'
alias runserver='python simple_app.py'
export FLASK_APP=simple_app.py
export FLASK_ENV=development
export PYTHONPATH=/workspace:$PYTHONPATH
export TERM=xterm-256color
cd /workspace 2>/dev/null || cd /
EOF

# Source bashrc
source ~/.bashrc

echo ""
echo "================================================"
echo "  Container Ready!"
echo "================================================"
echo ""
echo "Python: $(python3 --version 2>&1)"
echo "Working directory: $(pwd)"
echo ""
echo "Commands:"
echo "  python simple_app.py  - Start the Flask app"
echo "  pytest tests/         - Run tests"
echo "================================================"
echo ""

# IMPORTANT: Keep container running with an interactive bash shell
# This prevents the container from exiting
exec /bin/bash --login