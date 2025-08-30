# Email Management Tool - Advanced UV Setup Script
# Handles environment setup using UV for fast dependency management

$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'

# Configuration
$PYTHON_VERSION = "3.11"
$PROJECT_NAME = "email-management-tool"
$VENV_NAME = ".venv"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Step { Write-Host "`n→ $args" -ForegroundColor Magenta }

# Banner
Clear-Host
Write-Host @"
╔════════════════════════════════════════════════════════════╗
║           EMAIL MANAGEMENT TOOL - UV SETUP                 ║
║                Fast Python Environment Setup                ║
╚════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to install UV
function Install-UV {
    Write-Step "Installing UV package manager..."
    
    # Check if UV is already installed
    if (Test-Command "uv") {
        $uvVersion = uv --version
        Write-Success "✓ UV already installed: $uvVersion"
        return $true
    }
    
    # Install UV using the official installer
    try {
        Write-Info "Downloading UV installer..."
        $installer = "$env:TEMP\uv-installer.ps1"
        
        # Download the installer script
        Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $installer
        
        # Run the installer
        & powershell -ExecutionPolicy Bypass -File $installer
        
        # Add UV to PATH for current session
        $uvPath = "$env:USERPROFILE\.cargo\bin"
        if ($env:Path -notlike "*$uvPath*") {
            $env:Path = "$uvPath;$env:Path"
        }
        
        # Verify installation
        if (Test-Command "uv") {
            Write-Success "✓ UV installed successfully"
            return $true
        } else {
            throw "UV installation completed but command not found"
        }
    } catch {
        Write-Warning "Failed to install UV automatically: $_"
        Write-Info @"

Manual installation instructions:
1. Visit: https://github.com/astral-sh/uv
2. Download the Windows installer
3. Run the installer and follow instructions
4. Restart this setup script

Alternative (using pip):
  pip install uv
"@
        return $false
    }
}

# Function to setup Python environment with UV
function Setup-Environment {
    Write-Step "Setting up Python environment with UV..."
    
    try {
        # Create virtual environment with specific Python version
        Write-Info "Creating virtual environment with Python $PYTHON_VERSION..."
        uv venv $VENV_NAME --python $PYTHON_VERSION
        
        if (Test-Path "$VENV_NAME") {
            Write-Success "✓ Virtual environment created"
        } else {
            throw "Virtual environment creation failed"
        }
        
        # Create pyproject.toml for modern Python project
        Write-Info "Creating pyproject.toml..."
        $pyprojectContent = @"
[project]
name = "$PROJECT_NAME"
version = "1.0.0"
description = "Email Management Tool - Enterprise email moderation system"
readme = "README.md"
requires-python = ">=$PYTHON_VERSION"
dependencies = [
    "flask>=3.0.0",
    "sqlalchemy>=2.0.0",
    "aiosmtpd>=1.4.0",
    "flask-login>=0.6.0",
    "flask-wtf>=1.2.0",
    "werkzeug>=3.0.0",
    "bcrypt>=4.0.0",
    "python-dotenv>=1.0.0",
    "email-validator>=2.0.0",
    "python-dateutil>=2.8.0",
    "jinja2>=3.1.0",
    "markupsafe>=2.1.0",
    "itsdangerous>=2.1.0",
    "click>=8.1.0",
    "colorama>=0.4.0",
    "cryptography>=41.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.11.0",
    "pytest-flask>=1.2.0",
    "pytest-benchmark>=4.0.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "isort>=5.12.0",
    "pre-commit>=3.3.0",
    "pylint>=2.17.0",
    "bandit>=1.7.0",
    "safety>=2.3.0",
]
test = [
    "faker>=19.0.0",
    "factory-boy>=3.3.0",
    "responses>=0.23.0",
    "freezegun>=1.2.0",
    "coverage>=7.2.0",
    "pytest-html>=3.2.0",
    "pytest-xdist>=3.3.0",
    "pytest-timeout>=2.1.0",
    "locust>=2.15.0",
    "selenium>=4.10.0",
    "pytest-bdd>=6.1.0",
]
docs = [
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=1.3.0",
    "sphinx-autodoc-typehints>=1.23.0",
    "myst-parser>=2.0.0",
]

[build-system]
requires = ["setuptools>=68.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.uv]
dev-dependencies = []

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--verbose",
    "--strict-markers",
    "--tb=short",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--maxfail=1",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow tests",
    "smtp: SMTP-related tests",
    "imap: IMAP-related tests",
    "security: Security tests",
]

[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*", "*/test_*.py", "*/__pycache__/*"]

[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_unreachable = true
strict_equality = true

[tool.pylint.messages_control]
disable = "C0111,R0903,R0913,W0613"
"@
        $pyprojectContent | Out-File -FilePath "pyproject.toml" -Encoding UTF8
        Write-Success "✓ pyproject.toml created"
        
        # Install dependencies using UV
        Write-Info "Installing production dependencies with UV..."
        uv pip install -r requirements.txt
        
        Write-Info "Installing development dependencies..."
        uv pip install pytest pytest-cov pytest-asyncio pytest-mock pytest-flask faker
        
        Write-Success "✓ All dependencies installed"
        
        return $true
    } catch {
        Write-Error "Environment setup failed: $_"
        return $false
    }
}

# Function to create directory structure
function Create-ProjectStructure {
    Write-Step "Creating project structure..."
    
    $directories = @(
        "app",
        "app\models",
        "app\routes",
        "app\services",
        "app\utils",
        "config",
        "data",
        "logs",
        "templates",
        "static",
        "static\css",
        "static\js",
        "static\images",
        "tests",
        "tests\unit",
        "tests\unit\backend",
        "tests\unit\frontend",
        "tests\integration",
        "tests\e2e",
        "tests\performance",
        "tests\security",
        "tests\fixtures",
        "tests\mocks",
        "docs",
        "scripts",
        "backups",
        ".github",
        ".github\workflows"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Info "  Created: $dir"
        }
    }
    
    Write-Success "✓ Project structure created"
}

# Function to create test configuration
function Create-TestConfiguration {
    Write-Step "Creating test configuration..."
    
    # Create pytest.ini
    $pytestConfig = @"
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    -ra
    --strict-markers
    --ignore=docs
    --ignore=setup.py
    --ignore=.eggs
    --cov=app
    --cov-branch
    --cov-report=term-missing:skip-covered
    --cov-report=html:htmlcov
    --cov-report=xml
    --cov-fail-under=80
    --maxfail=1
    --tb=short
    --dist=load
    --numprocesses=auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Tests that take > 5 seconds
    smtp: SMTP protocol tests
    imap: IMAP protocol tests
    security: Security-related tests
    performance: Performance tests
    smoke: Quick smoke tests
"@
    $pytestConfig | Out-File -FilePath "pytest.ini" -Encoding UTF8
    Write-Success "✓ pytest.ini created"
    
    # Create .coveragerc
    $coverageConfig = @"
[run]
source = app
omit = 
    */tests/*
    */test_*.py
    */__pycache__/*
    */site-packages/*
    */.venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod

[html]
directory = htmlcov

[xml]
output = coverage.xml
"@
    $coverageConfig | Out-File -FilePath ".coveragerc" -Encoding UTF8
    Write-Success "✓ .coveragerc created"
}

# Function to install additional tools
function Install-Tools {
    Write-Step "Installing additional development tools..."
    
    try {
        # Install pre-commit
        Write-Info "Installing pre-commit hooks..."
        uv pip install pre-commit
        
        # Create pre-commit configuration
        $precommitConfig = @"
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=100", "--ignore=E203,W503"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
"@
        $precommitConfig | Out-File -FilePath ".pre-commit-config.yaml" -Encoding UTF8
        Write-Success "✓ Pre-commit configuration created"
        
        # Initialize git if not already initialized
        if (-not (Test-Path ".git")) {
            git init
            Write-Success "✓ Git repository initialized"
        }
        
        # Install pre-commit hooks
        pre-commit install
        Write-Success "✓ Pre-commit hooks installed"
        
        return $true
    } catch {
        Write-Warning "Some tools installation failed: $_"
        return $true  # Continue anyway
    }
}

# Function to create environment file
function Create-EnvironmentFile {
    Write-Step "Creating environment configuration..."
    
    $envContent = @"
# Email Management Tool - Environment Configuration
# Copy this file to .env and update with your values

# Application Settings
FLASK_APP=simple_app.py
FLASK_ENV=development
SECRET_KEY=$(New-Guid).ToString()
DEBUG=True

# Database
DATABASE_URL=sqlite:///data/email_moderation.db

# SMTP Proxy Settings
SMTP_PROXY_HOST=0.0.0.0
SMTP_PROXY_PORT=8587
MAX_MESSAGE_SIZE=33554432

# Web Interface
WEB_HOST=127.0.0.1
WEB_PORT=5000

# SMTP Relay (for sending approved emails)
SMTP_RELAY_HOST=smtp.gmail.com
SMTP_RELAY_PORT=587
SMTP_RELAY_USE_TLS=True
SMTP_RELAY_USERNAME=
SMTP_RELAY_PASSWORD=

# IMAP Settings (optional)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USE_SSL=True

# Security
SESSION_TIMEOUT=30
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=15
ENABLE_2FA=False

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/email_moderation.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Performance
WORKER_THREADS=4
CONNECTION_POOL_SIZE=20
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300

# Testing
TEST_DATABASE_URL=sqlite:///tests/test_db.sqlite
TEST_SMTP_PORT=8588
TEST_WEB_PORT=5001
"@
    
    $envContent | Out-File -FilePath ".env.example" -Encoding UTF8
    
    if (-not (Test-Path ".env")) {
        $envContent | Out-File -FilePath ".env" -Encoding UTF8
        Write-Success "✓ .env file created"
    }
    
    Write-Success "✓ Environment configuration created"
}

# Function to verify setup
function Verify-Setup {
    Write-Step "Verifying setup..."
    
    $checks = @()
    
    # Check UV installation
    if (Test-Command "uv") {
        $checks += "✓ UV installed"
    } else {
        $checks += "✗ UV not found"
    }
    
    # Check virtual environment
    if (Test-Path "$VENV_NAME") {
        $checks += "✓ Virtual environment created"
    } else {
        $checks += "✗ Virtual environment not found"
    }
    
    # Check dependencies
    if (Test-Path "$VENV_NAME\Scripts\flask.exe") {
        $checks += "✓ Flask installed"
    } else {
        $checks += "✗ Flask not found"
    }
    
    if (Test-Path "$VENV_NAME\Scripts\pytest.exe") {
        $checks += "✓ Pytest installed"
    } else {
        $checks += "✗ Pytest not found"
    }
    
    # Check project structure
    if ((Test-Path "app") -and (Test-Path "tests")) {
        $checks += "✓ Project structure created"
    } else {
        $checks += "✗ Project structure incomplete"
    }
    
    # Display results
    Write-Host "`n" -NoNewline
    Write-Info "Setup Verification Results:"
    foreach ($check in $checks) {
        if ($check -like "*✓*") {
            Write-Success "  $check"
        } else {
            Write-Error "  $check"
        }
    }
    
    $failed = $checks | Where-Object { $_ -like "*✗*" }
    return $failed.Count -eq 0
}

# Main execution
try {
    # Install UV
    if (-not (Install-UV)) {
        throw "UV installation failed. Please install manually and retry."
    }
    
    # Setup environment
    if (-not (Setup-Environment)) {
        throw "Environment setup failed."
    }
    
    # Create project structure
    Create-ProjectStructure
    
    # Create test configuration
    Create-TestConfiguration
    
    # Install additional tools
    Install-Tools
    
    # Create environment file
    Create-EnvironmentFile
    
    # Verify setup
    if (Verify-Setup) {
        Write-Host "`n" -NoNewline
        Write-Success @"
╔════════════════════════════════════════════════════════════╗
║                    SETUP COMPLETE!                         ║
╚════════════════════════════════════════════════════════════╝

Next steps:
1. Activate environment: .\.venv\Scripts\Activate.ps1
2. Run tests: .\test-all.bat
3. Start application: .\start-app.bat
4. View dashboard: http://localhost:5000

Quick commands:
- uv pip list              # List installed packages
- uv pip install <package> # Install new package
- pytest                   # Run all tests
- pytest -m unit          # Run unit tests only
- pytest --cov           # Run tests with coverage

"@
    } else {
        Write-Warning "Setup completed with some issues. Please review the verification results above."
    }
    
    exit 0
} catch {
    Write-Error "Setup failed: $_"
    exit 1
}