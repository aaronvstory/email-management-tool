# Email Management Tool - PowerShell Management Script
# Requires Administrator privileges for service installation

param(
    [Parameter(Position=0)]
    [ValidateSet('install', 'uninstall', 'start', 'stop', 'restart', 'status', 'backup', 'restore', 'logs', 'config')]
    [string]$Action = 'status'
)

$ErrorActionPreference = "Stop"
$AppName = "EmailManagementTool"
$AppPath = $PSScriptRoot
$VenvPath = Join-Path $AppPath ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$ServiceName = "EmailManagementService"
$ServiceDisplayName = "Email Management Tool Service"

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

# Banner
function Show-Banner {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   EMAIL MANAGEMENT TOOL - POWERSHELL MANAGER" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Install as Windows Service
function Install-Service {
    if (-not (Test-Administrator)) {
        Write-Error "Administrator privileges required to install service!"
        Write-Warning "Please run PowerShell as Administrator"
        return
    }

    Write-Info "Installing Email Management Tool as Windows Service..."
    
    # Create service wrapper script
    $serviceScript = @"
import sys
import os
sys.path.insert(0, r'$AppPath')
os.chdir(r'$AppPath')

# Import and run the application
from simple_app import *

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Start SMTP server in thread
    smtp_thread = threading.Thread(target=run_smtp_server, daemon=True)
    smtp_thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
"@
    
    $serviceScript | Out-File -FilePath (Join-Path $AppPath "service_wrapper.py") -Encoding UTF8
    
    # Install using NSSM (Non-Sucking Service Manager) if available
    $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
    
    if ($nssmPath) {
        nssm install $ServiceName $PythonExe (Join-Path $AppPath "service_wrapper.py")
        nssm set $ServiceName DisplayName $ServiceDisplayName
        nssm set $ServiceName Description "Email moderation and management system"
        nssm set $ServiceName Start SERVICE_AUTO_START
        nssm set $ServiceName AppDirectory $AppPath
        Write-Success "Service installed successfully using NSSM"
    } else {
        # Create using sc.exe
        $binPath = "`"$PythonExe`" `"$(Join-Path $AppPath 'service_wrapper.py')`""
        sc.exe create $ServiceName binPath= $binPath DisplayName= $ServiceDisplayName start= auto
        Write-Success "Service installed successfully using SC"
        Write-Warning "For better service management, consider installing NSSM"
    }
}

# Uninstall Windows Service
function Uninstall-Service {
    if (-not (Test-Administrator)) {
        Write-Error "Administrator privileges required to uninstall service!"
        return
    }

    Write-Info "Uninstalling Email Management Tool Service..."
    
    # Stop service first
    Stop-Service -Name $ServiceName -ErrorAction SilentlyContinue
    
    # Check if NSSM is available
    $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
    
    if ($nssmPath) {
        nssm remove $ServiceName confirm
    } else {
        sc.exe delete $ServiceName
    }
    
    Write-Success "Service uninstalled successfully"
}

# Start the application
function Start-App {
    Write-Info "Starting Email Management Tool..."
    
    # Check if running as service
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    
    if ($service) {
        Start-Service -Name $ServiceName
        Write-Success "Service started successfully"
    } else {
        # Start as regular application
        $process = Start-Process -FilePath $PythonExe -ArgumentList "simple_app.py" -WorkingDirectory $AppPath -PassThru
        Write-Success "Application started (PID: $($process.Id))"
        Write-Info "Dashboard: http://localhost:5000"
        Write-Info "SMTP Proxy: localhost:8587"
    }
}

# Stop the application
function Stop-App {
    Write-Info "Stopping Email Management Tool..."
    
    # Check if running as service
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    
    if ($service -and $service.Status -eq 'Running') {
        Stop-Service -Name $ServiceName
        Write-Success "Service stopped successfully"
    } else {
        # Stop regular process
        $processes = Get-Process python* | Where-Object { $_.Path -like "*$AppPath*" }
        if ($processes) {
            $processes | Stop-Process -Force
            Write-Success "Application stopped"
        } else {
            Write-Warning "No running instances found"
        }
    }
}

# Restart the application
function Restart-App {
    Stop-App
    Start-Sleep -Seconds 2
    Start-App
}

# Show application status
function Show-Status {
    Write-Host ""
    Write-Info "=== Application Status ==="
    
    # Check service
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        $status = $service.Status
        $color = if ($status -eq 'Running') { 'Green' } else { 'Red' }
        Write-Host "Service Status: " -NoNewline
        Write-Host $status -ForegroundColor $color
    } else {
        Write-Warning "Service not installed"
    }
    
    # Check processes
    $processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$AppPath*" }
    if ($processes) {
        Write-Success "Application is running"
        foreach ($proc in $processes) {
            Write-Info "  PID: $($proc.Id) - Memory: $([math]::Round($proc.WorkingSet64/1MB, 2)) MB"
        }
    } else {
        Write-Warning "Application is not running"
    }
    
    # Check ports
    Write-Host ""
    Write-Info "=== Port Status ==="
    $smtp = Test-NetConnection -ComputerName localhost -Port 8587 -WarningAction SilentlyContinue
    $web = Test-NetConnection -ComputerName localhost -Port 5000 -WarningAction SilentlyContinue
    
    if ($smtp.TcpTestSucceeded) {
        Write-Success "SMTP Proxy (8587): Active"
    } else {
        Write-Warning "SMTP Proxy (8587): Inactive"
    }
    
    if ($web.TcpTestSucceeded) {
        Write-Success "Web Dashboard (5000): Active"
        Write-Info "Dashboard URL: http://localhost:5000"
    } else {
        Write-Warning "Web Dashboard (5000): Inactive"
    }
    
    # Check database
    Write-Host ""
    Write-Info "=== Database Status ==="
    $dbPath = Join-Path $AppPath "data\email_moderation.db"
    if (Test-Path $dbPath) {
        $dbInfo = Get-Item $dbPath
        Write-Success "Database exists"
        Write-Info "  Size: $([math]::Round($dbInfo.Length/1MB, 2)) MB"
        Write-Info "  Modified: $($dbInfo.LastWriteTime)"
    } else {
        Write-Warning "Database not found"
    }
}

# Backup database and config
function Backup-Data {
    Write-Info "Creating backup..."
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = Join-Path $AppPath "backups\backup_$timestamp"
    
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Backup database
    $dbPath = Join-Path $AppPath "data\email_moderation.db"
    if (Test-Path $dbPath) {
        Copy-Item $dbPath -Destination $backupDir
        Write-Success "Database backed up"
    }
    
    # Backup config
    $configPath = Join-Path $AppPath "config"
    if (Test-Path $configPath) {
        Copy-Item $configPath -Destination $backupDir -Recurse
        Write-Success "Configuration backed up"
    }
    
    # Create backup info
    @{
        Timestamp = $timestamp
        Date = Get-Date
        AppVersion = "1.0.0"
    } | ConvertTo-Json | Out-File -FilePath (Join-Path $backupDir "backup_info.json")
    
    Write-Success "Backup created: $backupDir"
}

# Restore from backup
function Restore-Data {
    $backupDir = Join-Path $AppPath "backups"
    
    if (-not (Test-Path $backupDir)) {
        Write-Error "No backups found"
        return
    }
    
    # List available backups
    $backups = Get-ChildItem $backupDir -Directory | Sort-Object Name -Descending
    
    if ($backups.Count -eq 0) {
        Write-Error "No backups found"
        return
    }
    
    Write-Info "Available backups:"
    for ($i = 0; $i -lt $backups.Count; $i++) {
        Write-Host "[$i] $($backups[$i].Name)"
    }
    
    $selection = Read-Host "Select backup number"
    $selectedBackup = $backups[$selection]
    
    if (-not $selectedBackup) {
        Write-Error "Invalid selection"
        return
    }
    
    Write-Warning "This will overwrite current data. Continue? (Y/N)"
    $confirm = Read-Host
    
    if ($confirm -ne 'Y') {
        Write-Info "Restore cancelled"
        return
    }
    
    # Stop application first
    Stop-App
    
    # Restore database
    $dbBackup = Join-Path $selectedBackup.FullName "email_moderation.db"
    if (Test-Path $dbBackup) {
        Copy-Item $dbBackup -Destination (Join-Path $AppPath "data") -Force
        Write-Success "Database restored"
    }
    
    # Restore config
    $configBackup = Join-Path $selectedBackup.FullName "config"
    if (Test-Path $configBackup) {
        Copy-Item $configBackup -Destination $AppPath -Recurse -Force
        Write-Success "Configuration restored"
    }
    
    Write-Success "Restore completed from: $($selectedBackup.Name)"
}

# Show logs
function Show-Logs {
    param([int]$Lines = 50)
    
    $logPath = Join-Path $AppPath "logs\email_moderation.log"
    
    if (-not (Test-Path $logPath)) {
        Write-Warning "Log file not found"
        return
    }
    
    Write-Info "=== Recent Log Entries ==="
    Get-Content $logPath -Tail $Lines | ForEach-Object {
        if ($_ -match "ERROR") {
            Write-Error $_
        } elseif ($_ -match "WARNING") {
            Write-Warning $_
        } else {
            Write-Host $_
        }
    }
}

# Edit configuration
function Edit-Config {
    $configPath = Join-Path $AppPath "config\config.ini"
    
    if (-not (Test-Path $configPath)) {
        Write-Error "Configuration file not found"
        return
    }
    
    Write-Info "Opening configuration in notepad..."
    Start-Process notepad.exe -ArgumentList $configPath -Wait
    
    Write-Warning "Configuration changed. Restart required for changes to take effect."
    $restart = Read-Host "Restart now? (Y/N)"
    
    if ($restart -eq 'Y') {
        Restart-App
    }
}

# Main execution
Show-Banner

switch ($Action) {
    'install' { Install-Service }
    'uninstall' { Uninstall-Service }
    'start' { Start-App }
    'stop' { Stop-App }
    'restart' { Restart-App }
    'status' { Show-Status }
    'backup' { Backup-Data }
    'restore' { Restore-Data }
    'logs' { Show-Logs }
    'config' { Edit-Config }
    default { Show-Status }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan