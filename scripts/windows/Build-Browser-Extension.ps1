$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")

Push-Location $RepoRoot
try {
    Write-Host "Building SAPSOS browser extension from $RepoRoot"
    Write-Host ""

    corepack pnpm extension:package
    if ($LASTEXITCODE -ne 0) {
        throw "Extension package command failed. Review TypeScript build output above."
    }

    $OutputDir = Join-Path $RepoRoot "dist\extension-unpacked"
    Write-Host ""
    Write-Host "Browser extension package is ready." -ForegroundColor Green
    Write-Host "Generated extension build folder:"
    Write-Host $OutputDir
    Write-Host ""
    Write-Host "Manual load instructions:"
    Write-Host "1. Open Chrome or Edge."
    Write-Host "2. Go to chrome://extensions or edge://extensions."
    Write-Host "3. Enable Developer Mode."
    Write-Host "4. Click Load unpacked."
    Write-Host "5. Select the generated extension build folder."
}
catch {
    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
