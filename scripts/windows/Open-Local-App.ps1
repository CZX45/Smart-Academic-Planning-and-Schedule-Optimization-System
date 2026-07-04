$ErrorActionPreference = "Stop"

$WebPort = if ($env:LOCAL_WEB_PORT) { $env:LOCAL_WEB_PORT } elseif ($env:PLAYWRIGHT_WEB_PORT) { $env:PLAYWRIGHT_WEB_PORT } else { "3000" }
$WebUrl = "http://localhost:$WebPort"

try {
    Write-Host "Opening Smart Academic Planner local web app:"
    Write-Host $WebUrl
    Start-Process $WebUrl
}
catch {
    Write-Host "[FAIL] Could not open $WebUrl. Open it manually in Chrome or Edge." -ForegroundColor Red
    exit 1
}
