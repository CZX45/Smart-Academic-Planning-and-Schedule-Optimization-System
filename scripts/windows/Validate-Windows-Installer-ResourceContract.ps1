[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$NsisScriptRoot,
    [Parameter(Mandatory = $true)][string]$PayloadArchivePath,
    [Parameter(Mandatory = $true)][string]$PayloadMetadataPath,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = "Stop"

function Get-Sha256([string]$PathValue) {
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash([IO.File]::ReadAllBytes($PathValue))) -replace '-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

if (-not (Test-Path -LiteralPath $NsisScriptRoot -PathType Container)) {
    throw "Generated NSIS script root was not found: $NsisScriptRoot"
}
if (-not (Test-Path -LiteralPath $PayloadArchivePath -PathType Leaf)) {
    throw "Runtime payload archive was not found: $PayloadArchivePath"
}
if (-not (Test-Path -LiteralPath $PayloadMetadataPath -PathType Leaf)) {
    throw "Runtime payload metadata was not found: $PayloadMetadataPath"
}

$scripts = @(Get-ChildItem -LiteralPath $NsisScriptRoot -Filter "installer.nsi" -File -Recurse)
if ($scripts.Count -ne 1) {
    throw "Expected exactly one generated installer.nsi; found $($scripts.Count)."
}
$scriptPath = $scripts[0].FullName
$scriptText = Get-Content -LiteralPath $scriptPath -Raw
$requiredPatterns = @(
    '(?im)^\s*File\b[^\r\n]*/oname=[^\r\n]*PLUGINSDIR[^\r\n]*runtime-payload\.zip[^\r\n]*$',
    '(?im)^\s*File\b[^\r\n]*/oname=[^\r\n]*PLUGINSDIR[^\r\n]*runtime-payload-metadata\.json[^\r\n]*$',
    '(?i)-PayloadArchivePath[^\r\n]*PLUGINSDIR[^\r\n]*runtime-payload\.zip',
    '(?i)-PayloadMetadataPath[^\r\n]*PLUGINSDIR[^\r\n]*runtime-payload-metadata\.json'
)
foreach ($pattern in $requiredPatterns) {
    if ($scriptText -notmatch $pattern) {
        throw "Generated NSIS resource contract is missing pattern: $pattern"
    }
}
if ($scriptText -match '(?i)File\s+/a\s+"/oname=runtime-payload(?:-metadata)?\.(?:zip|json)"') {
    throw "Generated NSIS script still embeds a transient payload at $INSTDIR."
}

$metadata = Get-Content -LiteralPath $PayloadMetadataPath -Raw | ConvertFrom-Json
$archiveHash = Get-Sha256 $PayloadArchivePath
if ($metadata.archive_sha256.ToLowerInvariant() -ne $archiveHash) {
    throw "Runtime payload archive hash does not match metadata."
}

$contract = [ordered]@{
    schema_version = 1
    delivery_mode = "nsis_plugin_directory_transient"
    nsis_script_sha256 = Get-Sha256 $scriptPath
    resources = @(
        [ordered]@{
            name = "runtime-payload.zip"
            source = "dist/installer-stage/runtime-payload.zip"
            target = '$PLUGINSDIR\runtime-payload.zip'
            bytes = (Get-Item -LiteralPath $PayloadArchivePath).Length
            sha256 = $archiveHash
        },
        [ordered]@{
            name = "runtime-payload-metadata.json"
            source = "dist/installer-stage/runtime-payload-metadata.json"
            target = '$PLUGINSDIR\runtime-payload-metadata.json'
            bytes = (Get-Item -LiteralPath $PayloadMetadataPath).Length
            sha256 = Get-Sha256 $PayloadMetadataPath
        }
    )
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
$contract | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output "Validated generated NSIS transient resource contract."
Write-Output "NSIS script SHA256: $($contract.nsis_script_sha256)"
