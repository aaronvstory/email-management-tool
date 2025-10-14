#!/bin/bash
# Post-create script for Email Management Tool container

set -e

echo "=========================================="
echo "  Setting up Email Management Tool..."
echo "=========================================="

# Ensure we're in the workspace
cd /workspace

# Update package list
apt-get update

# Install additional system dependencies if needed
apt-get install -y --no-install-recommends \
    sqlite3 \
    nano \
    vim \
    curl \
    git \
    build-essential

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
else
    echo "No requirements.txt found, installing core dependencies..."
    pip install flask flask-login flask-wtf flask-limiter flask-cors \
                aiosmtpd cryptography bcrypt imapclient pytest \
                python-dotenv beautifulsoup4 email-validator
fi

# Create necessary directories
echo "Creating project directories..."
mkdir -p app/{routes,services,models,utils,workers}
mkdir -p templates
mkdir -p static/{css,js,images}
mkdir -p scripts
mkdir -p tests
mkdir -p logs
mkdir -p archive

# Generate encryption key if not exists
if [ ! -f "key.txt" ]; then
    echo "Generating encryption key..."
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > key.txt
    chmod 600 key.txt
fi

# Create .env from example if not exists
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

# Initialize database if needed
if [ ! -f "email_manager.db" ]; then
    echo "Initializing database..."
    python3 -c "
import sqlite3
conn = sqlite3.connect('email_manager.db')
cursor = conn.cursor()

# Create basic tables structure
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS email_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_address TEXT UNIQUE NOT NULL,
        imap_host TEXT,
        imap_port INTEGER,
        smtp_host TEXT,
        smtp_port INTEGER,
        imap_username TEXT,
        imap_password TEXT,
        smtp_username TEXT,
        smtp_password TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS email_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT,
        sender TEXT,
        recipients TEXT,
        subject TEXT,
        body_text TEXT,
        body_html TEXT,
        raw_content TEXT,
        status TEXT DEFAULT 'PENDING',
        interception_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()
print('Database initialized successfully')
" || echo "Database initialization skipped (may already exist)"
fi

# Set proper permissions
chmod -R 755 /workspace
chmod 600 key.txt 2>/dev/null || true
chmod 664 email_manager.db 2>/dev/null || true

# Configure bash
cat > /root/.bashrc << 'EOF'
# Email Management Tool Container Configuration

export PS1='\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '

# Aliases
alias ll='ls -alF --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias python='python3'
alias pip='pip3'
alias runserver='python simple_app.py'

# Environment
export FLASK_APP=simple_app.py
export FLASK_ENV=development
export FLASK_DEBUG=1
export PYTHONPATH=/workspace:$PYTHONPATH
export PATH=/workspace/scripts:$PATH

# History
export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTCONTROL=ignoreboth
shopt -s histappend

# Welcome message
echo "=========================================="
echo "  Email Management Tool - Ready!"
echo "=========================================="
echo ""
echo "Python: $(python3 --version)"
echo "Working directory: $(pwd)"
echo ""
echo "Quick commands:"
echo "  runserver         - Start the Flask app"
echo "  pytest tests/     - Run tests"
echo "  python simple_app.py - Start manually"
echo ""
echo "Web interface will be available at:"
echo "  http://localhost:5000"
echo "=========================================="

# Navigate to workspace
cd /workspace 2>/dev/null || true
EOF

# Source the new bashrc
source /root/.bashrc

echo ""
echo "=========================================="
echo "  Setup completed successfully!"
echo "=========================================="
echo ""
echo "Container is ready to use!"
echo "To start the application, run:"
echo "  python simple_app.py"
echo ""