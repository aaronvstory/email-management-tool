#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host '🔐 Email Management Tool - Security Setup (PowerShell)' -ForegroundColor Cyan

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Test-Path .env)) {
  Write-Host 'Creating .env from .env.example...'
  Copy-Item .env.example .env
} else {
  Write-Host '✓ .env file exists'
}

function New-SecretHex {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
  ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''
}

$envPath = Join-Path (Get-Location) '.env'
$envContent = Get-Content $envPath -Raw
if ($envContent -notmatch '^FLASK_SECRET_KEY=' -or $envContent -match '^FLASK_SECRET_KEY=$') {
  Write-Host 'Generating FLASK_SECRET_KEY...'
  $secret = New-SecretHex
  if ($envContent -match '^FLASK_SECRET_KEY=') {
    ($envContent -replace '^FLASK_SECRET_KEY=.*', "FLASK_SECRET_KEY=$secret") | Set-Content $envPath -NoNewline
  } else {
    Add-Content $envPath "`nFLASK_SECRET_KEY=$secret"
  }
  Write-Host '✓ SECRET_KEY generated'
} else {
  Write-Host '✓ SECRET_KEY already configured'
}

Write-Host ''
Write-Host '✅ Security setup complete!'
Write-Host ''
Write-Host 'Next steps:'
Write-Host '  1) Review .env and adjust values if needed'
Write-Host '  2) Start app: python simple_app.py'
Write-Host '  3) Run validation: .\validate_security.sh (Git Bash) or python scripts\validate_security.py'
