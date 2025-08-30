# Email Management Tool - PowerShell Test Runner
# Comprehensive test suite execution with reporting

param(
    [Parameter(Position=0)]
    [ValidateSet('all', 'unit', 'integration', 'e2e', 'performance', 'security', 'smtp', 'imap', 'quick')]
    [string]$TestSuite = 'all',
    
    [switch]$Coverage,
    [switch]$Verbose,
    [switch]$Html,
    [switch]$Parallel
)

$ErrorActionPreference = "Continue"

# Configuration
$VENV_PATH = ".venv"
$TEST_DIR = "tests"
$COVERAGE_DIR = "htmlcov"
$REPORT_DIR = "test-reports"

# Colors for output
function Write-TestHeader { 
    param($Text)
    Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║ $($Text.PadRight(58)) ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
}

function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Failure { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Warning { Write-Host "⚠ $args" -ForegroundColor Yellow }
function Write-Info { Write-Host "→ $args" -ForegroundColor Cyan }

# Banner
Clear-Host
Write-Host @"
╔════════════════════════════════════════════════════════════════════╗
║              EMAIL MANAGEMENT TOOL - TEST SUITE                    ║
║                    Comprehensive Testing Framework                  ║
╚════════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

Write-Host "`nTest Configuration:" -ForegroundColor Yellow
Write-Host "  Suite: $TestSuite" -ForegroundColor White
Write-Host "  Coverage: $($Coverage -eq $true)" -ForegroundColor White
Write-Host "  Parallel: $($Parallel -eq $true)" -ForegroundColor White
Write-Host "  HTML Report: $($Html -eq $true)" -ForegroundColor White

# Function to check environment
function Test-Environment {
    Write-TestHeader "ENVIRONMENT CHECK"
    
    $checks = @()
    
    # Check virtual environment
    if (Test-Path "$VENV_PATH\Scripts\python.exe") {
        Write-Success "Virtual environment found"
        $checks += $true
    } else {
        Write-Failure "Virtual environment not found"
        Write-Info "Run setup-uv.bat to create environment"
        $checks += $false
    }
    
    # Check pytest installation
    if (Test-Path "$VENV_PATH\Scripts\pytest.exe") {
        Write-Success "Pytest installed"
        $checks += $true
    } else {
        Write-Failure "Pytest not installed"
        $checks += $false
    }
    
    # Check test directory
    if (Test-Path $TEST_DIR) {
        $testFiles = Get-ChildItem -Path $TEST_DIR -Recurse -Filter "test_*.py"
        Write-Success "Found $($testFiles.Count) test files"
        $checks += $true
    } else {
        Write-Failure "Test directory not found"
        $checks += $false
    }
    
    return -not ($checks -contains $false)
}

# Function to run specific test suite
function Run-TestSuite {
    param(
        [string]$Suite,
        [string]$Marker = "",
        [string]$Description = ""
    )
    
    Write-TestHeader $Description
    
    # Build pytest command
    $pytestCmd = @("$VENV_PATH\Scripts\pytest.exe")
    
    # Add test directory or specific path
    if ($Suite -eq "all") {
        $pytestCmd += $TEST_DIR
    } else {
        $pytestCmd += $TEST_DIR
        if ($Marker) {
            $pytestCmd += "-m", $Marker
        }
    }
    
    # Add options
    if ($Verbose) {
        $pytestCmd += "-vv"
    } else {
        $pytestCmd += "-v"
    }
    
    if ($Coverage) {
        $pytestCmd += "--cov=app", "--cov-report=term-missing", "--cov-report=html"
    }
    
    if ($Html) {
        $pytestCmd += "--html=$REPORT_DIR/$Suite-report.html", "--self-contained-html"
    }
    
    if ($Parallel) {
        $pytestCmd += "-n", "auto"
    }
    
    # Add color output
    $pytestCmd += "--color=yes"
    
    # Execute tests
    Write-Info "Executing: $($pytestCmd -join ' ')"
    $startTime = Get-Date
    
    & $pytestCmd[0] $pytestCmd[1..$pytestCmd.Length]
    $exitCode = $LASTEXITCODE
    
    $duration = (Get-Date) - $startTime
    Write-Info "Duration: $($duration.TotalSeconds.ToString('F2')) seconds"
    
    return $exitCode
}

# Function to run unit tests
function Run-UnitTests {
    $exitCode = Run-TestSuite -Suite "unit" -Marker "unit" -Description "UNIT TESTS"
    
    if ($exitCode -eq 0) {
        Write-Success "Unit tests passed"
    } else {
        Write-Failure "Unit tests failed"
    }
    
    return $exitCode
}

# Function to run integration tests
function Run-IntegrationTests {
    $exitCode = Run-TestSuite -Suite "integration" -Marker "integration" -Description "INTEGRATION TESTS"
    
    if ($exitCode -eq 0) {
        Write-Success "Integration tests passed"
    } else {
        Write-Failure "Integration tests failed"
    }
    
    return $exitCode
}

# Function to run E2E tests
function Run-E2ETests {
    $exitCode = Run-TestSuite -Suite "e2e" -Marker "e2e" -Description "END-TO-END TESTS"
    
    if ($exitCode -eq 0) {
        Write-Success "E2E tests passed"
    } else {
        Write-Failure "E2E tests failed"
    }
    
    return $exitCode
}

# Function to run performance tests
function Run-PerformanceTests {
    $exitCode = Run-TestSuite -Suite "performance" -Marker "performance" -Description "PERFORMANCE TESTS"
    
    if ($exitCode -eq 0) {
        Write-Success "Performance tests passed"
    } else {
        Write-Failure "Performance tests failed"
    }
    
    return $exitCode
}

# Function to run security tests
function Run-SecurityTests {
    $exitCode = Run-TestSuite -Suite "security" -Marker "security" -Description "SECURITY TESTS"
    
    if ($exitCode -eq 0) {
        Write-Success "Security tests passed"
    } else {
        Write-Failure "Security tests failed"
    }
    
    return $exitCode
}

# Function to run SMTP tests
function Run-SMTPTests {
    $exitCode = Run-TestSuite -Suite "smtp" -Marker "smtp" -Description "SMTP PROTOCOL TESTS"
    
    if ($exitCode -eq 0) {
        Write-Success "SMTP tests passed"
    } else {
        Write-Failure "SMTP tests failed"
    }
    
    return $exitCode
}

# Function to run IMAP tests
function Run-IMAPTests {
    $exitCode = Run-TestSuite -Suite "imap" -Marker "imap" -Description "IMAP PROTOCOL TESTS"
    
    if ($exitCode -eq 0) {
        Write-Success "IMAP tests passed"
    } else {
        Write-Failure "IMAP tests failed"
    }
    
    return $exitCode
}

# Function to run quick smoke tests
function Run-QuickTests {
    Write-TestHeader "QUICK SMOKE TESTS"
    
    $pytestCmd = @(
        "$VENV_PATH\Scripts\pytest.exe",
        $TEST_DIR,
        "-m", "not slow",
        "--maxfail=3",
        "-x",
        "--tb=short",
        "--color=yes"
    )
    
    Write-Info "Running quick smoke tests..."
    & $pytestCmd[0] $pytestCmd[1..$pytestCmd.Length]
    
    return $LASTEXITCODE
}

# Function to generate test report
function Generate-TestReport {
    Write-TestHeader "TEST REPORT GENERATION"
    
    # Create report directory
    if (-not (Test-Path $REPORT_DIR)) {
        New-Item -ItemType Directory -Path $REPORT_DIR | Out-Null
    }
    
    # Generate coverage report
    if ($Coverage -and (Test-Path $COVERAGE_DIR)) {
        Write-Info "Coverage report available at: $COVERAGE_DIR\index.html"
        
        # Open coverage report in browser
        if ($Html) {
            Start-Process "$COVERAGE_DIR\index.html"
        }
    }
    
    # Generate test summary
    $summary = @"
====================================
TEST EXECUTION SUMMARY
====================================
Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Test Suite: $TestSuite
Coverage Enabled: $Coverage
Parallel Execution: $Parallel

RESULTS:
"@
    
    $summary | Out-File -FilePath "$REPORT_DIR\test-summary.txt"
    Write-Info "Test summary saved to: $REPORT_DIR\test-summary.txt"
}

# Main execution
try {
    # Check environment
    if (-not (Test-Environment)) {
        Write-Failure "Environment check failed. Please run setup-uv.bat first."
        exit 1
    }
    
    # Activate virtual environment
    $env:Path = "$PWD\$VENV_PATH\Scripts;$env:Path"
    
    # Create report directory
    if ($Html -and -not (Test-Path $REPORT_DIR)) {
        New-Item -ItemType Directory -Path $REPORT_DIR | Out-Null
    }
    
    # Run appropriate test suite
    $exitCode = 0
    
    switch ($TestSuite) {
        'all' {
            Write-Info "Running complete test suite..."
            
            $results = @()
            $results += Run-UnitTests
            $results += Run-IntegrationTests
            $results += Run-E2ETests
            
            if ($results -contains 1) {
                $exitCode = 1
            }
        }
        'unit' {
            $exitCode = Run-UnitTests
        }
        'integration' {
            $exitCode = Run-IntegrationTests
        }
        'e2e' {
            $exitCode = Run-E2ETests
        }
        'performance' {
            $exitCode = Run-PerformanceTests
        }
        'security' {
            $exitCode = Run-SecurityTests
        }
        'smtp' {
            $exitCode = Run-SMTPTests
        }
        'imap' {
            $exitCode = Run-IMAPTests
        }
        'quick' {
            $exitCode = Run-QuickTests
        }
    }
    
    # Generate report
    Generate-TestReport
    
    # Display final results
    Write-Host "`n" -NoNewline
    if ($exitCode -eq 0) {
        Write-Host @"
╔════════════════════════════════════════════════════════════════════╗
║                        TESTS PASSED ✓                              ║
╚════════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
    } else {
        Write-Host @"
╔════════════════════════════════════════════════════════════════════╗
║                        TESTS FAILED ✗                              ║
╚════════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Red
    }
    
    # Show coverage if enabled
    if ($Coverage) {
        Write-Host "`nCoverage Report:" -ForegroundColor Yellow
        & "$VENV_PATH\Scripts\coverage.exe" report --skip-covered --skip-empty
    }
    
    exit $exitCode
    
} catch {
    Write-Failure "Test execution failed: $_"
    exit 1
}