#!/bin/bash
# Terminal Fix Script for Codex Container
# This script fixes common terminal connectivity issues

echo "====================================="
echo "  Fixing Terminal Connection Issues  "
echo "====================================="

# Set proper terminal environment
export TERM=xterm-256color
export SHELL=/bin/bash
export PS1='\u@container:\w\$ '

# Ensure bash is the default shell
if [ ! -f /bin/bash ]; then
    echo "Installing bash..."
    apt-get update && apt-get install -y bash
fi

# Create a proper bashrc if missing
if [ ! -f "$HOME/.bashrc" ]; then
    cat > "$HOME/.bashrc" << 'EOF'
#!/bin/bash
# Terminal configuration for Email Management Tool

# Set prompt
export PS1='\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '

# Basic aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias cls='clear'
alias python='python3'
alias pip='pip3'

# Flask environment
export FLASK_APP=simple_app.py
export FLASK_ENV=development
export PYTHONPATH=/workspace:$PYTHONPATH

# Terminal settings
export TERM=xterm-256color
shopt -s checkwinsize

# History settings
HISTCONTROL=ignoreboth
HISTSIZE=10000
HISTFILESIZE=20000

# Navigate to workspace
cd /workspace 2>/dev/null || cd /

# Welcome message
echo "Email Management Tool - Container Ready"
echo "Run: python simple_app.py to start"
EOF
    echo "Created new .bashrc configuration"
fi

# Source the bashrc
source "$HOME/.bashrc" 2>/dev/null || true

# Test bash availability
if bash -c "echo 'Bash test successful'" 2>/dev/null; then
    echo "✓ Bash is working correctly"
else
    echo "✗ Bash test failed - trying to fix..."

    # Try to reinstall bash
    apt-get update && apt-get install --reinstall -y bash

    # Create a shell wrapper
    cat > /usr/local/bin/shell-wrapper << 'EOF'
#!/bin/sh
exec /bin/bash --login "$@"
EOF
    chmod +x /usr/local/bin/shell-wrapper

    # Update alternatives
    update-alternatives --install /bin/sh sh /bin/bash 100
fi

# Ensure Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found - installing..."
    apt-get update && apt-get install -y python3 python3-pip
fi

# Install minimal requirements if missing
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing minimal Python requirements..."
    pip3 install flask aiosmtpd cryptography
fi

# Create workspace directory if missing
mkdir -p /workspace
cd /workspace 2>/dev/null || cd /

# Final check
echo ""
echo "====================================="
echo "  Terminal Fix Complete"
echo "====================================="
echo ""
echo "Terminal environment configured:"
echo "  Shell: $SHELL"
echo "  Term: $TERM"
echo "  Python: $(python3 --version 2>&1)"
echo "  Working Dir: $(pwd)"
echo ""
echo "If terminal is still disconnecting:"
echo "1. Restart the container"
echo "2. Try: exec /bin/bash --login"
echo "3. Check container logs for errors"
echo ""

# Keep terminal alive
exec /bin/bash --login