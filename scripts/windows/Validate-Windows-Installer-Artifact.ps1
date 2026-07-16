[CmdletBinding()]
param(
    [string]$ManifestPath = "dist\windows-installer\packaging-manifest.json",
    [string]$ExpectedCommit = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$manifestFile = if ([IO.Path]::IsPathRooted($ManifestPath)) {
    $ManifestPath
} else {
    Join-Path $repoRoot $ManifestPath
}
if (-not (Test-Path -LiteralPath $manifestFile -PathType Leaf)) {
    throw "Packaging manifest was not found: $manifestFile"
}

$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
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
if ($manifest.components.fastapi_runtime -ne "dist/local-desktop-api/sapsos-api") {
    throw "FastAPI runtime is missing from the packaging contract."
}
if ($manifest.components.static_web -ne "dist/local-desktop-web") {
    throw "Static Web export is missing from the packaging contract."
}
if ($manifest.components.required_runtime_resources -notcontains "index.html") {
    throw "index.html is missing from the packaging contract."
}
if ($ExpectedCommit -and $manifest.commit -ne $ExpectedCommit) {
    throw "Artifact commit mismatch: expected '$ExpectedCommit', found '$($manifest.commit)'."
}

$artifactPath = Join-Path (Split-Path -Parent $manifestFile) $manifest.installer.path
if (-not (Test-Path -LiteralPath $artifactPath -PathType Leaf)) {
    throw "Installer artifact referenced by the manifest is missing: $artifactPath"
}
$artifact = Get-Item -LiteralPath $artifactPath
$hash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($artifact.Length -ne [int64]$manifest.installer.bytes) {
    throw "Installer byte count does not match the manifest."
}
if ($hash -ne $manifest.installer.sha256.ToLowerInvariant()) {
    throw "Installer SHA-256 does not match the manifest."
}

Write-Output "Validated installer artifact: $($artifact.Name)"
Write-Output "SHA256: $hash"
