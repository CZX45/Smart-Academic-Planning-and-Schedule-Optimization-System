[CmdletBinding()]
param(
    [string]$ManifestPath = "dist\windows-installer\packaging-manifest.json",
    [string]$ExpectedCommit = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Get-Sha256([string]$PathValue) {
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $sha256.ComputeHash([IO.File]::ReadAllBytes($PathValue))
        return ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}
$manifestFile = if ([IO.Path]::IsPathRooted($ManifestPath)) {
    $ManifestPath
} else {
    Join-Path $repoRoot $ManifestPath
}
if (-not (Test-Path -LiteralPath $manifestFile -PathType Leaf)) {
    throw "Packaging manifest was not found: $manifestFile"
}

$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
$manifestText = Get-Content -LiteralPath $manifestFile -Raw
if ($manifestText -match '(?i)[A-Z]:[\\/]|next-env\.d\.ts|localize-web-ui-zh-cn\.patch|\.codex-worktrees') {
    throw "Packaging manifest contains an absolute or protected path."
}
if ($manifest.schema_version -ne 1) { throw "Unsupported packaging manifest schema." }
if ($manifest.product.install_scope -ne "per-user") { throw "Artifact is not marked per-user." }
if ($manifest.product.bundle_identifier -ne "com.sapsos.smart-academic-planner") {
    throw "Artifact bundle identifier is not the stable SAPSOS identity."
}
if ($manifest.product.data_directory -ne "%LOCALAPPDATA%\SAPSOS") {
    throw "Artifact data-directory policy drifted."
}
if ($manifest.product_mode -ne "LOCAL_DESKTOP") { throw "Artifact is not LOCAL_DESKTOP." }
if ($manifest.signed -ne $false) { throw "Unsigned foundation artifact must declare signed=false." }
if ($manifest.components.tauri_executable -ne "sapsos-local-desktop.exe") {
    throw "Tauri executable is missing from the packaging contract."
}
if ($manifest.components.fastapi_runtime -ne "dist/installer-stage/api") {
    throw "FastAPI runtime is missing from the packaging contract."
}
if ($manifest.components.static_web -ne "dist/installer-stage/web") {
    throw "Static Web export is missing from the packaging contract."
}
if ($manifest.components.required_runtime_resources -notcontains "index.html") {
    throw "index.html is missing from the packaging contract."
}
if (-not $manifest.staging_manifest) { throw "Staging manifest is missing from the packaging manifest." }
if (@($manifest.components.licenses_notices).Count -eq 0) { throw "License/notice contract is empty." }
foreach ($license in @($manifest.components.licenses_notices)) {
    if ($license -notmatch '^(?i)api/') { throw "License/notice path must be staged under API: $license" }
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ("dist/installer-stage/" + $license)) -PathType Leaf)) {
        throw "License/notice file is missing from staging: $license"
    }
}
foreach ($contract in @($manifest.contracts)) {
    if ([IO.Path]::IsPathRooted($contract)) { throw "Packaging contract path must be relative: $contract" }
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $contract) -PathType Leaf)) {
        throw "Packaging contract is missing: $contract"
    }
}
if ($ExpectedCommit -and $manifest.commit -ne $ExpectedCommit) {
    throw "Artifact commit mismatch: expected '$ExpectedCommit', found '$($manifest.commit)'."
}

$artifactPath = Join-Path (Split-Path -Parent $manifestFile) $manifest.installer.path
if (-not (Test-Path -LiteralPath $artifactPath -PathType Leaf)) {
    throw "Installer artifact referenced by the manifest is missing: $artifactPath"
}
$artifact = Get-Item -LiteralPath $artifactPath
if ($artifact.Name -ne $manifest.product.installer_artifact_name.Replace("{version}", $manifest.product.version)) {
    throw "Installer file name does not match the stable artifact convention."
}
if ($artifact.Length -le 0) { throw "Installer artifact is empty." }
$hash = Get-Sha256 $artifactPath
if ($artifact.Length -ne [int64]$manifest.installer.bytes) {
    throw "Installer byte count does not match the manifest."
}
if ($hash -ne $manifest.installer.sha256.ToLowerInvariant()) {
    throw "Installer SHA-256 does not match the manifest."
}

$stagingPath = Join-Path (Split-Path -Parent $manifestFile) $manifest.staging_manifest
if (-not (Test-Path -LiteralPath $stagingPath -PathType Leaf)) {
    throw "Staging manifest referenced by the package manifest is missing: $stagingPath"
}
$staging = Get-Content -LiteralPath $stagingPath -Raw | ConvertFrom-Json
$stagingText = Get-Content -LiteralPath $stagingPath -Raw
if ($stagingText -match '(?i)[A-Z]:[\\/]|next-env\.d\.ts|localize-web-ui-zh-cn\.patch|\.codex-worktrees') {
    throw "Staging manifest contains an absolute or protected path."
}
if ($staging.schema_version -ne 1 -or $staging.product_mode -ne "LOCAL_DESKTOP") {
    throw "Staging manifest schema or product mode is invalid."
}
foreach ($component in @("fastapi_runtime", "static_web")) {
    $records = @($staging.components.$component)
    if ($records.Count -eq 0) { throw "Staging manifest component is empty: $component" }
    foreach ($record in $records) {
        if ([IO.Path]::IsPathRooted($record.path) -or $record.path -match '(?i)(^|[\\/])(?:\.env|.*\.(?:db|sqlite|sapsos-backup)$|pairing\.json$|runtime\.json$|credentials?|tokens?|tests?|fixtures?)') {
            throw "Forbidden or absolute staged path: $($record.path)"
        }
        $sourcePath = Join-Path $repoRoot $record.path
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "Staged file is missing from the committed build output: $($record.path)"
        }
        $source = Get-Item -LiteralPath $sourcePath
        if ($source.Length -ne [int64]$record.bytes) { throw "Staged file size mismatch: $($record.path)" }
        $sourceHash = Get-Sha256 $sourcePath
        if ($sourceHash -ne $record.sha256.ToLowerInvariant()) { throw "Staged file hash mismatch: $($record.path)" }
    }
}

Write-Output "Validated installer artifact: $($artifact.Name)"
Write-Output "SHA256: $hash"
