param(
  [string]$BaseUrl = $env:SNAP_BASE_URL,
  [switch]$Headful,
  [string]$Out = "snapshots",
  [string]$Pages,
  [string]$Elements
)
$env:SNAP_BASE_URL = $BaseUrl
$headfulFlag = if ($Headful.IsPresent) { "--headful" } else { "" }
$pagesArg   = if ($Pages) { "--pages $Pages" } else { "" }
$elemArg    = if ($Elements) { "--elements $Elements" } else { "" }
cmd /c "npm run snap -- --base-url $BaseUrl --out $Out $headfulFlag $pagesArg $elemArg"
