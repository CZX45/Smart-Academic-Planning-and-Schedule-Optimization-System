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
foreach ($requiredResource in @("runtime/sapsos-api/sapsos-api.exe", "runtime/sapsos-api/MSVCP140.dll")) {
    if ($manifest.components.required_runtime_resources -notcontains $requiredResource) {
        throw "Required packaged runtime resource is missing from the packaging contract: $requiredResource"
    }
}
if ($manifest.components.runtime_payload_archive -ne "runtime-payload.zip") {
    throw "Runtime payload archive is missing from the packaging contract."
}
foreach ($transientResource in @("runtime-payload.zip", "runtime-payload-metadata.json")) {
    if (@($manifest.components.installer_transient_resources) -notcontains $transientResource) {
        throw "Installer transient resource is missing from the packaging contract: $transientResource"
    }
}
if (-not $manifest.provenance -or -not $manifest.provenance.source_head_sha) {
    throw "Packaging manifest is missing source-head provenance."
}
if (-not $manifest.installer_resource_contract) {
    throw "Installer resource contract is missing from the packaging manifest."
}
$resourceContractPath = Join-Path (Split-Path -Parent $manifestFile) $manifest.installer_resource_contract
if (-not (Test-Path -LiteralPath $resourceContractPath -PathType Leaf)) {
    throw "Installer resource contract file is missing: $resourceContractPath"
}
$resourceContract = Get-Content -LiteralPath $resourceContractPath -Raw | ConvertFrom-Json
if ($resourceContract.delivery_mode -ne "nsis_plugin_directory_transient") {
    throw "Installer resource delivery mode is not explicit and transient."
}
foreach ($resourceName in @("runtime-payload.zip", "runtime-payload-metadata.json")) {
    $resource = @($resourceContract.resources) | Where-Object { $_.name -eq $resourceName } | Select-Object -First 1
    if (-not $resource) { throw "Installer resource contract is missing: $resourceName" }
    if ($resource.target -notlike '$PLUGINSDIR\*') { throw "Installer resource is not owned by PLUGINSDIR: $resourceName" }
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
$payloadArchivePath = Join-Path $repoRoot "dist/installer-stage/runtime-payload.zip"
$payloadMetadataPath = Join-Path $repoRoot "dist/installer-stage/runtime-payload-metadata.json"
if (-not (Test-Path -LiteralPath $payloadArchivePath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $payloadMetadataPath -PathType Leaf)) {
    throw "Runtime payload archive or metadata is missing from staging."
}
$payloadMetadata = Get-Content -LiteralPath $payloadMetadataPath -Raw | ConvertFrom-Json
if ($payloadMetadata.archive_sha256.ToLowerInvariant() -ne (Get-Sha256 $payloadArchivePath)) {
    throw "Runtime payload archive hash does not match its metadata."
}
foreach ($requiredRuntimeFile in @("sapsos-api.exe", "MSVCP140.dll")) {
    if (@($payloadMetadata.required_runtime_files) -notcontains $requiredRuntimeFile) {
        throw "Runtime payload metadata does not require: $requiredRuntimeFile"
    }
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
        if ([IO.Path]::IsPathRooted($record.path) -or $record.path -match '(?i)(^|[\\/])(?:\.env(?:[\\/]|$)|.*\.(?:db|sqlite|sapsos-backup)$|pairing\.json$|runtime\.json$|credentials?(?:[\\/]|$)|tokens?(?:[\\/]|$)|tests?(?:[\\/]|$)|fixtures?(?:[\\/]|$))') {
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
