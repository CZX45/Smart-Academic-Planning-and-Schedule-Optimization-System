[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ArtifactRoot,
    [Parameter(Mandatory = $true)][string]$InstallerVersion,
    [Parameter(Mandatory = $true)][string]$TestRoot,
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
$artifactRoot = (Resolve-Path $ArtifactRoot).Path
$manifestPath = Join-Path $artifactRoot "packaging-manifest.json"
$resourceContractPath = Join-Path $artifactRoot "installer-resource-contract.json"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Downloaded artifact packaging manifest is missing." }
if (-not (Test-Path -LiteralPath $resourceContractPath -PathType Leaf)) { throw "Downloaded artifact resource contract is missing." }

function Get-Sha256([string]$PathValue) {
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash([IO.File]::ReadAllBytes($PathValue))) -replace '-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}
function Assert-True([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$contract = Get-Content -LiteralPath $resourceContractPath -Raw | ConvertFrom-Json
$installerName = $manifest.product.installer_artifact_name.Replace("{version}", $manifest.product.version)
$installerPath = Join-Path $artifactRoot $installerName
Assert-True ($manifest.product.version -eq $InstallerVersion) "Artifact version does not match the round-trip version."
Assert-True ($installerName -eq $manifest.installer.path) "Artifact installer path does not match the manifest."
Assert-True (Test-Path -LiteralPath $installerPath -PathType Leaf) "Downloaded installer is missing: $installerPath"
$installer = Get-Item -LiteralPath $installerPath
$installerHash = Get-Sha256 $installerPath
Assert-True ($installer.Length -eq [int64]$manifest.installer.bytes) "Downloaded installer byte count differs from manifest."
Assert-True ($installerHash -eq $manifest.installer.sha256.ToLowerInvariant()) "Downloaded installer SHA-256 differs from manifest."
Assert-True ($contract.delivery_mode -eq "nsis_plugin_directory_transient") "Artifact does not declare explicit transient resource delivery."
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$manifest.provenance.source_head_sha)) "Artifact has no source-head provenance."

$root = [IO.Path]::GetFullPath($TestRoot).TrimEnd('\', '/')
if ([IO.Path]::GetPathRoot($root) -eq $root) { throw "Round-trip test root cannot be a drive root." }
if (Test-Path -LiteralPath $root) { throw "Round-trip test root must not already exist: $root" }
$installRoot = Join-Path $root "Programs\SAPSOS Local Desktop"
$dataRoot = Join-Path $root "SAPSOS"
$tempRoot = Join-Path $root "Temp"
New-Item -ItemType Directory -Force -Path $root, $dataRoot, $tempRoot | Out-Null
$sentinel = Join-Path $dataRoot "roundtrip-user-data.sentinel"
Set-Content -LiteralPath $sentinel -Value "preserve" -Encoding UTF8
$oldLocalAppData = $env:LOCALAPPDATA
$oldTemp = $env:TEMP
$oldTmp = $env:TMP
$summary = [ordered]@{
    artifact_root = "<artifact-root>"
    installer = $installerName
    installer_version = $InstallerVersion
    installer_sha256 = $installerHash
    source_head_sha = $manifest.provenance.source_head_sha
    workflow_sha = $manifest.provenance.workflow_sha
    install_root = "<isolated-install-root>"
    diagnostic_record = $null
    installed_runtime = $false
    transient_resources_delivered = $false
    user_data_preserved = $false
}

try {
    $env:LOCALAPPDATA = $root
    $env:TEMP = $tempRoot
    $env:TMP = $tempRoot
    $process = Start-Process -FilePath $installerPath -ArgumentList @("/S", "/D=$installRoot") -PassThru
    $deadline = [DateTime]::UtcNow.AddMinutes(5)
    while (-not $process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
    }
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "Exact artifact installer did not exit within five minutes."
    }
    Assert-True ($process.ExitCode -eq 0) "Exact artifact installer failed with exit code $($process.ExitCode)."
    $appPath = Join-Path $installRoot "sapsos-local-desktop.exe"
    $runtimeRoot = Join-Path $installRoot "runtime\sapsos-api"
    Assert-True (Test-Path -LiteralPath $appPath -PathType Leaf) "Exact artifact install did not produce the desktop executable."
    Assert-True (Test-Path -LiteralPath (Join-Path $runtimeRoot "sapsos-api.exe") -PathType Leaf) "Exact artifact install did not produce sapsos-api.exe."
    Assert-True (Test-Path -LiteralPath (Join-Path $runtimeRoot "MSVCP140.dll") -PathType Leaf) "Exact artifact install did not produce MSVCP140.dll."
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $installRoot "runtime-payload.zip"))) "Transient archive leaked into the final install root."
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $installRoot "runtime-payload-metadata.json"))) "Transient metadata leaked into the final install root."
    $summary.installed_runtime = $true
    $summary.transient_resources_delivered = $true

    $diagnosticRoot = Join-Path $tempRoot "SAPSOS\installer-runtime"
    $recordFile = Get-ChildItem -LiteralPath $diagnosticRoot -Filter "runtime-install-*.json" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    Assert-True ($null -ne $recordFile) "Exact artifact install did not persist runtime diagnostics."
    $record = Get-Content -LiteralPath $recordFile.FullName -Raw | ConvertFrom-Json
    Assert-True ($record.status -eq "succeeded") "Exact artifact runtime diagnostic did not succeed."
    Assert-True ($record.payload_archive_exists -eq $true) "Runtime diagnostic did not prove archive delivery before validation."
    Assert-True ($record.payload_metadata_exists -eq $true) "Runtime diagnostic did not prove metadata delivery before validation."
    Assert-True ($record.source_payload_path -and $record.source_payload_path -notlike "$installRoot*") "Runtime archive was not delivered from an explicit transient path."
    Assert-True ($record.source_metadata_path -and $record.source_metadata_path -notlike "$installRoot*") "Runtime metadata was not delivered from an explicit transient path."
    Assert-True ($record.provenance.source_head_sha -eq $manifest.provenance.source_head_sha) "Runtime diagnostic source head differs from artifact manifest."
    $summary.diagnostic_record = $recordFile.Name
    $summary.user_data_preserved = (Get-Content -LiteralPath $sentinel -Raw).TrimEnd() -eq "preserve"
    Assert-True $summary.user_data_preserved "Round-trip altered user data sentinel."
    $summary | ConvertTo-Json -Depth 10
} finally {
    if ($oldLocalAppData) { $env:LOCALAPPDATA = $oldLocalAppData } elseif (Test-Path Env:LOCALAPPDATA) { Remove-Item Env:LOCALAPPDATA }
    if ($oldTemp) { $env:TEMP = $oldTemp } elseif (Test-Path Env:TEMP) { Remove-Item Env:TEMP }
    if ($oldTmp) { $env:TMP = $oldTmp } elseif (Test-Path Env:TMP) { Remove-Item Env:TMP }
    if ($EvidencePath) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null
        $summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
    }
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }
}
