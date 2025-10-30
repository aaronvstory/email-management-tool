param(
  [string]$BaseUrl = "http://localhost:5000",
  [string]$OutDir = "snapshots"
)
$env:SNAP_BASE_URL = $BaseUrl
$env:SNAP_OUT_DIR = $OutDir
npm run snap
