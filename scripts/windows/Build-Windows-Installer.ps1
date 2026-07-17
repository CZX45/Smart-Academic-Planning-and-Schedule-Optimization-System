[CmdletBinding()]
param(
    [string]$OutputRoot = "dist\windows-installer"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$identityPath = Join-Path $repoRoot "desktop-shell\desktop-identity.json"
$identity = Get-Content $identityPath -Raw | ConvertFrom-Json
$cleanup = Join-Path $PSScriptRoot "Invoke-SafeBuildCleanup.ps1"

function Invoke-Checked([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

& (Join-Path $PSScriptRoot "Validate-Desktop-Identity.ps1")
if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    throw "Corepack is required for the shared/OpenAPI/Web release pipeline."
}
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    throw "Cargo is required for the Tauri Windows release pipeline."
}

$distRoot = Join-Path $repoRoot "dist"
$outputPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $OutputRoot))
if (Test-Path -LiteralPath $outputPath) {
    & $cleanup -TargetPath $outputPath -AllowedBuildRoot $distRoot
}
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

# Keep this one entry point deterministic: no stage may consume a stale output
# from an earlier Web/API/Tauri build.
Invoke-Checked "corepack" @("pnpm", "--filter", "@sapsos/shared", "build") "Shared package build failed."
Invoke-Checked "corepack" @("pnpm", "openapi:check") "OpenAPI/generated-client validation failed."
Invoke-Checked "corepack" @("pnpm", "--filter", "@sapsos/shared", "build") "Shared package rebuild after OpenAPI validation failed."

& (Join-Path $PSScriptRoot "Build-Web-UI.ps1")
if ($LASTEXITCODE -ne 0) { throw "Static Web export failed." }
& (Join-Path $PSScriptRoot "Build-FastAPI-Runtime.ps1")
if ($LASTEXITCODE -ne 0) { throw "FastAPI runtime packaging failed." }
& (Join-Path $PSScriptRoot "Validate-FastAPI-Runtime.ps1")

$apiRoot = Join-Path $repoRoot "dist\local-desktop-api\sapsos-api"
$webRoot = Join-Path $repoRoot "dist\local-desktop-web"
if (-not (Test-Path -LiteralPath (Join-Path $webRoot "index.html") -PathType Leaf)) {
    throw "Static Web export is missing index.html."
}

function Get-Sha256([string]$PathValue) {
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $sha256.ComputeHash([IO.File]::ReadAllBytes($PathValue))
        return ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}
$stageRoot = Join-Path $repoRoot "dist\installer-stage"
$stageApiRoot = Join-Path $stageRoot "api"
$stageWebRoot = Join-Path $stageRoot "web"
if (Test-Path -LiteralPath $stageRoot) {
    & $cleanup -TargetPath $stageRoot -AllowedBuildRoot $distRoot
}
New-Item -ItemType Directory -Force -Path $stageApiRoot, $stageWebRoot | Out-Null
Get-ChildItem -LiteralPath $apiRoot -Force | Copy-Item -Destination $stageApiRoot -Recurse -Force
Get-ChildItem -LiteralPath $webRoot -Force | Copy-Item -Destination $stageWebRoot -Recurse -Force
if (-not (Test-Path -LiteralPath (Join-Path $stageApiRoot "sapsos-api.exe") -PathType Leaf)) {
    throw "Short API staging is missing the packaged executable."
}
if (-not (Test-Path -LiteralPath (Join-Path $stageWebRoot "index.html") -PathType Leaf)) {
    throw "Short Web staging is missing index.html."
}
$licenseFiles = @(Get-ChildItem -LiteralPath $stageApiRoot -Recurse -Force -File | Where-Object {
    $_.FullName -match '(?i)(^|[\\/])(license|licenses|notice|notices)([\\/]|$)|(?i)\\.dist-info[\\/]'
})
if ($licenseFiles.Count -eq 0) {
    throw "Packaged API staging contains no license or notice files."
}
$stagingManifest = Join-Path $outputPath "staging-manifest.json"
& (Join-Path $PSScriptRoot "Validate-Packaging-Staging.ps1") `
    -ApiRoot $stageApiRoot `
    -WebRoot $stageWebRoot `
    -ManifestPath $stagingManifest

$tauriRoot = Join-Path $repoRoot "desktop-shell\src-tauri"
$targetRoot = Join-Path $tauriRoot "target"
$bundleRoot = Join-Path $targetRoot "release\bundle\nsis"
if (Test-Path -LiteralPath $bundleRoot) {
    & $cleanup -TargetPath $bundleRoot -AllowedBuildRoot $targetRoot
}
New-Item -ItemType Directory -Force -Path $bundleRoot | Out-Null
& cargo tauri --version
if ($LASTEXITCODE -ne 0) { throw "The pinned Tauri CLI is unavailable. Install the CI-pinned tauri-cli version." }
Push-Location $tauriRoot
try {
    & cargo tauri build --bundles nsis --ci
    if ($LASTEXITCODE -ne 0) { throw "Tauri NSIS release build failed." }
} finally { Pop-Location }

$releaseExecutable = Join-Path $targetRoot "release\sapsos-local-desktop.exe"
if (-not (Test-Path -LiteralPath $releaseExecutable -PathType Leaf)) {
    throw "Tauri release executable is missing: $releaseExecutable"
}
if ((Get-Item -LiteralPath $releaseExecutable).Length -le 0) {
    throw "Tauri release executable is empty: $releaseExecutable"
}
$installers = @(Get-ChildItem -LiteralPath $bundleRoot -Filter "*-setup.exe" -File -ErrorAction SilentlyContinue)
if ($installers.Count -ne 1) { throw "Expected exactly one fresh NSIS setup artifact; found $($installers.Count)." }

$artifactName = $identity.installer_artifact_name.Replace("{version}", $identity.version)
$artifactPath = Join-Path $outputPath $artifactName
Copy-Item -LiteralPath $installers[0].FullName -Destination $artifactPath -Force
$hash = Get-Sha256 $artifactPath
$commit = (& git -C $repoRoot rev-parse HEAD).Trim()
$stageApiUri = [Uri]::new((Resolve-Path $stageApiRoot).Path.TrimEnd('\', '/') + '\')
$manifest = [ordered]@{
    schema_version = 1
    product = $identity
    commit = $commit
    product_mode = "LOCAL_DESKTOP"
    signed = $false
    staging_manifest = "staging-manifest.json"
    contracts = @("desktop-shell/desktop-identity.json", "desktop-shell/data-retention-contract.json")
    components = [ordered]@{
        tauri_executable = "sapsos-local-desktop.exe"
        fastapi_runtime = "dist/installer-stage/api"
        static_web = "dist/installer-stage/web"
        required_runtime_resources = @("index.html", "runtime/sapsos-api")
        licenses_notices = @($licenseFiles | ForEach-Object {
            $relative = [Uri]::UnescapeDataString(
                $stageApiUri.MakeRelativeUri([Uri]::new($_.FullName)).ToString()
            ).Replace('\', '/')
            "api/$relative"
        })
    }
    installer = [ordered]@{ path = $artifactName; bytes = (Get-Item $artifactPath).Length; sha256 = $hash }
    notes = @("NSIS per-user installer", "Code signing is not configured", "Installer-level E2E is a later milestone")
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputPath "packaging-manifest.json") -Encoding UTF8
& (Join-Path $PSScriptRoot "Validate-Windows-Installer-Artifact.ps1") -ManifestPath (Join-Path $OutputRoot "packaging-manifest.json") -ExpectedCommit $commit
Write-Output $artifactPath
