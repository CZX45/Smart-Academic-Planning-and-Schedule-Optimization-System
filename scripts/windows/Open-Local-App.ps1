$ErrorActionPreference = "Stop"

$WebUrl = "http://localhost:3000"

try {
    Write-Host "Opening Smart Academic Planner local web app:"
    Write-Host $WebUrl
    Start-Process $WebUrl
}
catch {
    Write-Host "[FAIL] Could not open $WebUrl. Open it manually in Chrome or Edge." -ForegroundColor Red
    exit 1
}
