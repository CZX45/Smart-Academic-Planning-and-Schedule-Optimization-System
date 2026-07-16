[CmdletBinding()]
param(
    [switch]$SkipApiBuild,
    [switch]$SkipWebBuild,
    [switch]$SkipTauriBuild,
    [string]$OutputRoot = "dist\windows-installer"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$identityPath = Join-Path $repoRoot "desktop-shell\desktop-identity.json"
$identity = Get-Content $identityPath -Raw | ConvertFrom-Json
& (Join-Path $PSScriptRoot "Validate-Desktop-Identity.ps1")

if (-not $SkipApiBuild) {
    & (Join-Path $PSScriptRoot "Build-FastAPI-Runtime.ps1")
    if ($LASTEXITCODE -ne 0) { throw "FastAPI runtime packaging failed." }
}
if (-not $SkipWebBuild) {
    & (Join-Path $PSScriptRoot "Build-Web-UI.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Web UI packaging failed." }
}

$apiExecutable = Join-Path $repoRoot "dist\local-desktop-api\sapsos-api\sapsos-api.exe"
$webIndex = Join-Path $repoRoot "dist\local-desktop-web\index.html"
if (-not (Test-Path -LiteralPath $apiExecutable)) { throw "FastAPI runtime is missing: $apiExecutable" }
if (-not (Test-Path -LiteralPath $webIndex)) { throw "Static Web export is missing: $webIndex" }

if (-not $SkipTauriBuild) {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { throw "Cargo is required for the Tauri NSIS build." }
    Push-Location (Join-Path $repoRoot "desktop-shell\src-tauri")
    try {
        & cargo tauri build --bundles nsis --ci
        if ($LASTEXITCODE -ne 0) { throw "Tauri NSIS packaging failed." }
    } finally { Pop-Location }
}

$bundleRoot = Join-Path $repoRoot "desktop-shell\src-tauri\target\release\bundle\nsis"
$installer = Get-ChildItem -LiteralPath $bundleRoot -Filter "*.exe" -File -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $installer) { throw "No NSIS installer was produced under $bundleRoot." }
$outputPath = Join-Path $repoRoot $OutputRoot
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$artifactName = $identity.installer_artifact_name.Replace("{version}", $identity.version)
$artifactPath = Join-Path $outputPath $artifactName
Copy-Item -LiteralPath $installer.FullName -Destination $artifactPath -Force
$hash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()
$commit = (& git -C $repoRoot rev-parse HEAD).Trim()
$manifest = [ordered]@{
    schema_version = 1
    product = $identity
    commit = $commit
    product_mode = "LOCAL_DESKTOP"
    signed = $false
    components = [ordered]@{
        tauri_executable = "sapsos-local-desktop.exe"
        fastapi_runtime = "dist/local-desktop-api/sapsos-api"
        static_web = "dist/local-desktop-web"
        required_runtime_resources = @("index.html", "runtime/sapsos-api")
        licenses_notices = @()
    }
    installer = [ordered]@{ path = $artifactName; bytes = (Get-Item $artifactPath).Length; sha256 = $hash }
    notes = @("NSIS per-user installer", "Code signing is not configured", "Installer-level E2E is a later milestone")
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputPath "packaging-manifest.json") -Encoding UTF8
& (Join-Path $PSScriptRoot "Validate-Windows-Installer-Artifact.ps1") -ManifestPath (Join-Path $OutputRoot "packaging-manifest.json") -ExpectedCommit $commit
Write-Output $artifactPath
