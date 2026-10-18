[CmdletBinding()]
param(
    [string]$OutputRoot = "dist\windows-installer",
    [string]$TestVersionOverride = "",
    [switch]$AllowTestVersionOverride
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$identityPath = Join-Path $repoRoot "desktop-shell\desktop-identity.json"
$identity = Get-Content $identityPath -Raw | ConvertFrom-Json
$cleanup = Join-Path $PSScriptRoot "Invoke-SafeBuildCleanup.ps1"
$effectiveVersion = $identity.version
if ($TestVersionOverride) {
    if (-not $AllowTestVersionOverride -or $env:CI -ne "true") {
        throw "Version overrides are restricted to an explicit Windows CI test invocation."
    }
    if ($TestVersionOverride -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') {
        throw "Test version override must be a valid semantic version."
    }
    $effectiveVersion = $TestVersionOverride
    $identity.version = $effectiveVersion
}

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
function Get-OptionalEnvironmentValue([string]$Name) {
    if (Test-Path -LiteralPath "Env:$Name") {
        $value = (Get-Item -LiteralPath "Env:$Name").Value
        if ($value) { return $value.Trim() }
    }
    return $null
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
$requiredRuntimeFiles = @("sapsos-api.exe", "MSVCP140.dll")
foreach ($requiredRuntimeFile in $requiredRuntimeFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $stageApiRoot $requiredRuntimeFile) -PathType Leaf)) {
        throw "Short API staging is missing required runtime file: $requiredRuntimeFile"
    }
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

$commit = (& git -C $repoRoot rev-parse HEAD).Trim()
$sourceHeadSha = Get-OptionalEnvironmentValue "SAPSOS_SOURCE_HEAD_SHA"
if (-not $sourceHeadSha) { $sourceHeadSha = $commit }
$workflowSha = Get-OptionalEnvironmentValue "SAPSOS_WORKFLOW_SHA"
$workflowRef = Get-OptionalEnvironmentValue "SAPSOS_WORKFLOW_REF"
$mergeRefSha = Get-OptionalEnvironmentValue "SAPSOS_MERGE_REF_SHA"
$payloadArchivePath = Join-Path $stageRoot "runtime-payload.zip"
if (Test-Path -LiteralPath $payloadArchivePath) {
    Remove-Item -LiteralPath $payloadArchivePath -Force
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory(
    $stageApiRoot,
    $payloadArchivePath,
    [IO.Compression.CompressionLevel]::Optimal,
    $false
)
$payloadHash = Get-Sha256 $payloadArchivePath
$payloadMetadataPath = Join-Path $stageRoot "runtime-payload-metadata.json"
[ordered]@{
    schema_version = 1
    source = "dist/installer-stage/api"
    commit = $commit
    build_commit = $commit
    source_head_sha = $sourceHeadSha
    workflow_sha = $workflowSha
    workflow_ref = $workflowRef
    merge_ref_sha = $mergeRefSha
    installer_version = $effectiveVersion
    archive_sha256 = $payloadHash
    required_runtime_files = $requiredRuntimeFiles
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $payloadMetadataPath -Encoding UTF8

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
    if (-not $TestVersionOverride) {
        & cargo tauri build --bundles nsis --ci
    } else {
        $tauriBuildArguments = @("tauri", "build", "--bundles", "nsis", "--ci")
        $versionConfig = Join-Path $outputPath "ci-version-override.json"
        '{"version":"' + $effectiveVersion + '"}' | Set-Content -LiteralPath $versionConfig -Encoding UTF8
        $tauriBuildArguments += @("--config", $versionConfig)
        & cargo @tauriBuildArguments
    }
    if ($LASTEXITCODE -ne 0) { throw "Tauri NSIS release build failed." }
} finally { Pop-Location }

$nsisResourceContractPath = Join-Path $outputPath "installer-resource-contract.json"
& (Join-Path $PSScriptRoot "Validate-Windows-Installer-ResourceContract.ps1") `
    -NsisScriptRoot (Join-Path $targetRoot "release\nsis") `
    -PayloadArchivePath $payloadArchivePath `
    -PayloadMetadataPath $payloadMetadataPath `
    -OutputPath $nsisResourceContractPath

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
$stageApiUri = [Uri]::new((Resolve-Path $stageApiRoot).Path.TrimEnd('\', '/') + '\')
$manifest = [ordered]@{
    schema_version = 1
    product = $identity
    commit = $commit
    provenance = [ordered]@{
        source_head_sha = $sourceHeadSha
        workflow_sha = $workflowSha
        workflow_ref = $workflowRef
        merge_ref_sha = $mergeRefSha
        build_commit = $commit
    }
    product_mode = "LOCAL_DESKTOP"
    signed = $false
    staging_manifest = "staging-manifest.json"
    contracts = @("desktop-shell/desktop-identity.json", "desktop-shell/data-retention-contract.json")
    components = [ordered]@{
        tauri_executable = "sapsos-local-desktop.exe"
        fastapi_runtime = "dist/installer-stage/api"
        static_web = "dist/installer-stage/web"
        required_runtime_resources = @("index.html", "runtime/sapsos-api/sapsos-api.exe", "runtime/sapsos-api/MSVCP140.dll")
        runtime_payload_archive = "runtime-payload.zip"
        installer_transient_resources = @("runtime-payload.zip", "runtime-payload-metadata.json")
        licenses_notices = @($licenseFiles | ForEach-Object {
            $relative = [Uri]::UnescapeDataString(
                $stageApiUri.MakeRelativeUri([Uri]::new($_.FullName)).ToString()
            ).Replace('\', '/')
            "api/$relative"
        })
    }
    installer_resource_contract = "installer-resource-contract.json"
    installer = [ordered]@{ path = $artifactName; bytes = (Get-Item $artifactPath).Length; sha256 = $hash }
    notes = @("NSIS per-user installer", "Code signing is not configured", "Installer-level E2E is a later milestone")
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputPath "packaging-manifest.json") -Encoding UTF8
& (Join-Path $PSScriptRoot "Validate-Windows-Installer-Artifact.ps1") -ManifestPath (Join-Path $OutputRoot "packaging-manifest.json") -ExpectedCommit $commit
Write-Output $artifactPath
