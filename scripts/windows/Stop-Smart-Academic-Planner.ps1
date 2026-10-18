$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")

Push-Location $RepoRoot
try {
    Write-Host "Stopping Smart Academic Planner local services from $RepoRoot"
    Write-Host ""

    docker compose down
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose stop failed. Run docker compose ps and docker compose logs for details."
    }

    Write-Host ""
    Write-Host "Smart Academic Planner local services stopped." -ForegroundColor Green
    Write-Host "Local PostgreSQL data volume was preserved."
    Write-Host ""
    Write-Host "Optional destructive reset, only when you intentionally want to delete local database data:"
    Write-Host "docker compose down -v"
}
catch {
    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
