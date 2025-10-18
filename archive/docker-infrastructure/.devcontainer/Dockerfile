FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    nano \
    vim \
    sqlite3 \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONPATH=/workspace \
    FLASK_APP=simple_app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TERM=xterm-256color \
    SHELL=/bin/bash

# Copy requirements first for better caching
COPY requirements.txt* ./

# Install Python dependencies
RUN if [ -f requirements.txt ]; then \
        pip install --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --upgrade pip && \
        pip install flask flask-login flask-wtf flask-limiter flask-cors \
                    aiosmtpd cryptography bcrypt imapclient pytest \
                    python-dotenv beautifulsoup4 email-validator; \
    fi

# Create necessary directories
RUN mkdir -p /workspace/{app,templates,static,scripts,tests,logs,archive}

# Configure bash
RUN echo '#!/bin/bash\n\
export PS1="\[\033[01;32m\]\u@email-tool\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "\n\
alias ll="ls -alF --color=auto"\n\
alias la="ls -A --color=auto"\n\
alias l="ls -CF --color=auto"\n\
alias python="python3"\n\
alias pip="pip3"\n\
alias runserver="python simple_app.py"\n\
export FLASK_APP=simple_app.py\n\
export FLASK_ENV=development\n\
export PYTHONPATH=/workspace:$PYTHONPATH\n\
cd /workspace 2>/dev/null || cd /\n\
echo "========================================"\n\
echo "  Email Management Tool Container"\n\
echo "========================================"\n\
echo ""\n\
echo "Commands:"\n\
echo "  python simple_app.py - Start the app"\n\
echo "  pytest tests/        - Run tests"\n\
echo "========================================"\n\
' > /root/.bashrc

# Make bash the default shell
RUN chsh -s /bin/bash root

# Expose ports
EXPOSE 5000 8587

# Default command - keep container running
CMD ["/bin/bash", "--login"]