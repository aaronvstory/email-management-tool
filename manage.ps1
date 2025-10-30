param(
  [ValidateSet('menu','start','snap','boot-snap-open','snap-open')]
  [string]$Task = 'menu',
  [string]$BaseUrl = 'http://localhost:5000',
  [switch]$Headful,
  [string]$Pages,
  [string]$Elements
)

function Load-SnapEnv {
  $snapEnv = ".\.snap.env"
  if (Test-Path $snapEnv) {
    Get-Content $snapEnv | ForEach-Object {
      if ($_ -match '^\s*#') { return }
      if ($_ -match '^\s*$') { return }
      $k,$v = $_.Split('=',2)
      [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim())
    }
    Write-Host "Loaded .snap.env" -ForegroundColor Green
  }
}

function Start-App {
  Write-Host "Starting app…" -ForegroundColor Cyan
  $env:FLASK_ENV = "development"
  Start-Process -NoNewWindow -FilePath "python" -ArgumentList "simple_app.py" -PassThru | Out-Null
  Wait-Port 5000
}

function Wait-Port([int]$Port) {
  Write-Host "Waiting for :$Port…"
  for ($i=0; $i -lt 60; $i++) {
    try { 
      (New-Object Net.Sockets.TcpClient("127.0.0.1",$Port)).Dispose()
      Write-Host "✓ Port $Port is ready" -ForegroundColor Green
      return
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  Write-Host "✗ Timeout waiting for port $Port" -ForegroundColor Red
}

function Run-Snap {
  Load-SnapEnv
  Write-Host "Running snapshots on $BaseUrl" -ForegroundColor Cyan
  $headful = if ($Headful.IsPresent) { "-Headful" } else { "" }
  $pages   = if ($Pages) { "-Pages `"$Pages`"" } else { "" }
  $elems   = if ($Elements) { "-Elements `"$Elements`"" } else { "" }
  $cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File tools/snapshots/snap.ps1 -BaseUrl $BaseUrl $headful $pages $elems"
  Invoke-Expression $cmd
}

function Open-LatestSnap {
  $root = Join-Path (Get-Location) "snapshots"
  if (!(Test-Path $root)) { 
    Write-Host "No snapshots folder yet." -ForegroundColor Yellow
    return 
  }
  $latest = Get-ChildItem $root | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($latest) { 
    Write-Host "Opening latest snapshot folder: $($latest.Name)" -ForegroundColor Green
    Start-Process explorer.exe $latest.FullName 
  }
}

switch ($Task) {
  'start' { 
    Start-App
    break 
  }
  'snap' { 
    Run-Snap
    break 
  }
  'snap-open' { 
    Run-Snap
    Open-LatestSnap
    break 
  }
  'boot-snap-open' { 
    Start-App
    Run-Snap
    Open-LatestSnap
    break 
  }
  default {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Email Manager – Development Utility" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 <task> [options]" -ForegroundColor White
    Write-Host ""
    Write-Host "TASKS:" -ForegroundColor Yellow
    Write-Host "  start               " -NoNewline -ForegroundColor White
    Write-Host "Start Flask server" -ForegroundColor Gray
    Write-Host "  snap                " -NoNewline -ForegroundColor White
    Write-Host "Capture screenshots" -ForegroundColor Gray
    Write-Host "  snap-open           " -NoNewline -ForegroundColor White
    Write-Host "Capture + open folder" -ForegroundColor Gray
    Write-Host "  boot-snap-open      " -NoNewline -ForegroundColor White
    Write-Host "Boot server → snap → open" -ForegroundColor Gray
    Write-Host "  menu                " -NoNewline -ForegroundColor White
    Write-Host "Show this menu (default)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "OPTIONS:" -ForegroundColor Yellow
    Write-Host "  -BaseUrl <url>      " -NoNewline -ForegroundColor White
    Write-Host "Base URL (default: http://localhost:5000)" -ForegroundColor Gray
    Write-Host "  -Headful            " -NoNewline -ForegroundColor White
    Write-Host "Show browser during capture" -ForegroundColor Gray
    Write-Host "  -Pages <keys>       " -NoNewline -ForegroundColor White
    Write-Host "Comma-separated page keys (e.g., 'dashboard,emails')" -ForegroundColor Gray
    Write-Host "  -Elements <sels>    " -NoNewline -ForegroundColor White
    Write-Host "Comma-separated CSS selectors (e.g., '.page-header,.email-table')" -ForegroundColor Gray
    Write-Host ""
    Write-Host "EXAMPLES:" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 boot-snap-open" -ForegroundColor Cyan
    Write-Host "  .\manage.ps1 snap -Headful -Pages 'dashboard,emails'" -ForegroundColor Cyan
    Write-Host "  .\manage.ps1 snap -Elements '.page-header,.email-table'" -ForegroundColor Cyan
    Write-Host ""
  }
}
