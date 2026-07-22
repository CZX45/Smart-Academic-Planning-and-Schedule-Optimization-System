[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallRoot,
    [string]$PayloadArchivePath = "",
    [string]$PayloadMetadataPath = "",
    [string]$InstallerVersion = "",
    [string]$DiagnosticDirectory = "",
    [switch]$BeginAttempt,
    [switch]$RemoveInstalledRuntime,
    [switch]$TestMode,
    [int]$SimulateWin32ErrorCode = 0,
    [string]$SimulateFailurePath = "MSVCP140.dll"
)

$ErrorActionPreference = "Stop"
$retryLimit = 3
$retryDelayMilliseconds = 250
$requiredFallbackFiles = @("sapsos-api.exe", "MSVCP140.dll")

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-FullPath([string]$PathValue) {
    return [IO.Path]::GetFullPath($PathValue).TrimEnd('\', '/')
}

function Get-Sha256([string]$PathValue) {
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash([IO.File]::ReadAllBytes($PathValue))) -replace '-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

function Get-Win32ErrorCode([object]$ErrorRecord) {
    $native = $ErrorRecord.Exception.PSObject.Properties['NativeErrorCode']
    if ($native -and $null -ne $native.Value) { return [int]$native.Value }
    $hresultHex = ([int]$ErrorRecord.Exception.HResult).ToString("X8")
    if ($hresultHex.StartsWith("8007", [StringComparison]::OrdinalIgnoreCase)) {
        return [Convert]::ToInt32($hresultHex.Substring(4), 16)
    }
    return $null
}

function Get-ErrorCategory([int]$Code, [object]$ErrorRecord) {
    switch ($Code) {
        2 { return "file_not_found" }
        3 { return "path_not_found" }
        5 { return "access_denied" }
        32 { return "sharing_violation" }
        33 { return "lock_violation" }
        default {
            if ($ErrorRecord.Exception -is [IO.IOException]) { return "av_or_interference_unknown" }
            return "other_win32_error"
        }
    }
}

function Get-PathAttributes([string]$PathValue) {
    if (-not (Test-Path -LiteralPath $PathValue)) { return $null }
    return ([string](Get-Item -LiteralPath $PathValue -Force).Attributes)
}

function Write-Record([object]$Record, [string]$PathValue) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $PathValue) | Out-Null
    $Record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $PathValue -Encoding UTF8
}

function New-AttemptRecord([string]$InstallRootValue, [string]$RuntimePathValue) {
    $rootExists = Test-Path -LiteralPath $InstallRootValue -PathType Container
    $appPath = Join-Path $InstallRootValue "sapsos-local-desktop.exe"
    $runtimeExists = Test-Path -LiteralPath $RuntimePathValue -PathType Container
    $runtimeComplete = $runtimeExists -and
        (Test-Path -LiteralPath (Join-Path $RuntimePathValue "sapsos-api.exe") -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $RuntimePathValue "MSVCP140.dll") -PathType Leaf)
    $mode = if (-not (Test-Path -LiteralPath $appPath -PathType Leaf) -and -not $runtimeExists) { "clean_install" }
        elseif (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) { "partial_install" }
        elseif (-not $runtimeComplete) { "partial_install" }
        else {
            $version = (Get-Item -LiteralPath $appPath -ErrorAction SilentlyContinue).VersionInfo.ProductVersion
            if ($version -and $InstallerVersion -and $version -like "$InstallerVersion*") { "repair" } else { "upgrade" }
        }
    return [ordered]@{
        schema_version = 1
        status = "in_progress"
        started_at = (Get-Date).ToUniversalTime().ToString("o")
        completed_at = $null
        installer_version = $InstallerVersion
        build_commit = $null
        phase = "nsis_payload_copy"
        final_outcome = $null
        install_mode = $mode
        install_root = $InstallRootValue
        destination_path = $RuntimePathValue
        destination_existed_before = $runtimeExists
        destination_attributes = Get-PathAttributes $RuntimePathValue
        source_payload_path = $PayloadArchivePath
        source_payload_identity = $null
        windows_error_code = $null
        windows_error_category = $null
        windows_error_message = $null
        retry_count = 0
    }
}

function Find-LatestAttempt([string]$InstallRootValue) {
    if (-not (Test-Path -LiteralPath $DiagnosticDirectory -PathType Container)) { return $null }
    return Get-ChildItem -LiteralPath $DiagnosticDirectory -Filter "runtime-install-*.json" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        ForEach-Object {
            try {
                $candidate = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
                if ($candidate.install_root -eq $InstallRootValue -and $candidate.status -eq "in_progress") {
                    return [pscustomobject]@{ Record = $candidate; Path = $_.FullName }
                }
            } catch { }
        } | Select-Object -First 1
}

function New-SimulatedError([int]$Code) {
    throw [System.ComponentModel.Win32Exception]::new($Code, "Simulated Windows failure for installer test mode.")
}

function Invoke-WithRetry([scriptblock]$Operation, [string]$RelativePath, [object]$Record) {
    $attempt = 0
    while ($true) {
        try {
            if ($TestMode -and $SimulateWin32ErrorCode -gt 0 -and
                $RelativePath -ieq $SimulateFailurePath) {
                New-SimulatedError $SimulateWin32ErrorCode
            }
            & $Operation
            return
        } catch {
            $code = Get-Win32ErrorCode $_
            $category = Get-ErrorCategory $code $_
            $Record.windows_error_code = $code
            $Record.windows_error_category = $category
            $Record.windows_error_message = $_.Exception.Message
            $Record.retry_count = $attempt
            $retryable = $code -in @(32, 33)
            if (-not $retryable -or $attempt -ge $retryLimit) { throw }
            $attempt++
            $Record.retry_count = $attempt
            Start-Sleep -Milliseconds $retryDelayMilliseconds
        }
    }
}

function Assert-WithinDirectory([string]$RootPath, [string]$CandidatePath) {
    $root = (Get-FullPath $RootPath) + '\'
    $candidate = Get-FullPath $CandidatePath
    if (-not $candidate.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Payload entry escapes the staging directory."
    }
}

function Get-RuntimeRequiredFiles([object]$Metadata) {
    $files = @($Metadata.required_runtime_files)
    if ($files.Count -eq 0) { $files = $requiredFallbackFiles }
    if ($files -notcontains "sapsos-api.exe" -or $files -notcontains "MSVCP140.dll") {
        throw "Payload metadata does not require the complete packaged runtime."
    }
    return $files
}

if (-not $DiagnosticDirectory) {
    $DiagnosticDirectory = Join-Path ([IO.Path]::GetTempPath()) "SAPSOS\installer-runtime"
}
$InstallRoot = Get-FullPath $InstallRoot
$runtimePath = Get-FullPath (Join-Path $InstallRoot "runtime\sapsos-api")

if ($RemoveInstalledRuntime) {
    try {
        if (Test-Path -LiteralPath $runtimePath -PathType Container) {
            [IO.Directory]::Delete($runtimePath, $true)
        }
        foreach ($payloadPath in @(
                (Join-Path $InstallRoot "runtime-payload.zip"),
                (Join-Path $InstallRoot "runtime-payload-metadata.json")
            )) {
            if (Test-Path -LiteralPath $payloadPath -PathType Leaf) {
                [IO.File]::Delete($payloadPath)
            }
        }
        Write-Output "Installed runtime payload removed."
        exit 0
    } catch {
        Write-Error "Installed runtime payload cleanup failed: $($_.Exception.Message)"
        exit 1
    }
}

if ($BeginAttempt) {
    $record = New-AttemptRecord $InstallRoot $runtimePath
    $attemptPath = Join-Path $DiagnosticDirectory "runtime-install-$([Guid]::NewGuid().ToString('N')).json"
    Write-Record $record $attemptPath
    Write-Output "Runtime installer attempt recorded: $attemptPath"
    exit 0
}

$attempt = Find-LatestAttempt $InstallRoot
if ($attempt) {
    $record = $attempt.Record
    $attemptPath = $attempt.Path
} else {
    $record = New-AttemptRecord $InstallRoot $runtimePath
    $attemptPath = Join-Path $DiagnosticDirectory "runtime-install-$([Guid]::NewGuid().ToString('N')).json"
    Write-Record $record $attemptPath
}

$runtimeParent = Split-Path -Parent $runtimePath
$temporaryStageRoot = Join-Path ([IO.Path]::GetTempPath()) "SAPSOS\runtime-stage"
$stagePath = Join-Path $temporaryStageRoot ([Guid]::NewGuid().ToString('N'))
if (-not [StringComparer]::OrdinalIgnoreCase.Equals(
        [IO.Path]::GetPathRoot($stagePath),
        [IO.Path]::GetPathRoot($runtimePath))) {
    $stagePath = Join-Path $runtimeParent ".sapsos-runtime-stage-$([Guid]::NewGuid().ToString('N'))"
}
$temporaryBackupRoot = Join-Path ([IO.Path]::GetTempPath()) "SAPSOS\runtime-backup"
$backupPath = Join-Path $temporaryBackupRoot ([Guid]::NewGuid().ToString('N'))
if (-not [StringComparer]::OrdinalIgnoreCase.Equals(
        [IO.Path]::GetPathRoot($backupPath),
        [IO.Path]::GetPathRoot($runtimePath))) {
    $backupPath = Join-Path $runtimeParent ".sapsos-runtime-backup-$([Guid]::NewGuid().ToString('N'))"
}
$backupCreated = $false
$destinationReplaced = $false
$zip = $null

try {
    $record.phase = "payload_validation"
    if (-not (Test-Path -LiteralPath $PayloadArchivePath -PathType Leaf)) {
        throw "Runtime payload archive is missing."
    }
    if (-not (Test-Path -LiteralPath $PayloadMetadataPath -PathType Leaf)) {
        throw "Runtime payload metadata is missing."
    }
    $metadata = Get-Content -LiteralPath $PayloadMetadataPath -Raw | ConvertFrom-Json
    $requiredFiles = Get-RuntimeRequiredFiles $metadata
    $archiveHash = Get-Sha256 $PayloadArchivePath
    if ($metadata.archive_sha256 -and $metadata.archive_sha256.ToLowerInvariant() -ne $archiveHash) {
        throw "Runtime payload archive hash does not match its metadata."
    }
    $record.build_commit = $metadata.commit
    $record.source_payload_path = $PayloadArchivePath
    $record.source_payload_identity = [ordered]@{
        archive_sha256 = $archiveHash
        metadata_schema_version = $metadata.schema_version
        source = $metadata.source
    }
    Write-Record $record $attemptPath

    New-Item -ItemType Directory -Force -Path $runtimeParent, $stagePath, (Split-Path -Parent $backupPath) | Out-Null
    $zip = [IO.Compression.ZipFile]::OpenRead($PayloadArchivePath)
    foreach ($entry in $zip.Entries) {
        $relativePath = $entry.FullName.Replace('\', '/')
        if ([string]::IsNullOrWhiteSpace($relativePath) -or $relativePath.EndsWith('/')) { continue }
        $targetPath = Get-FullPath (Join-Path $stagePath $relativePath)
        Assert-WithinDirectory $stagePath $targetPath
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetPath) | Out-Null
        Invoke-WithRetry {
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetPath, $false)
        } $relativePath $record
    }
    $zip.Dispose(); $zip = $null
    foreach ($required in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $stagePath $required) -PathType Leaf)) {
            throw "Required runtime file is missing from the staged payload: $required"
        }
    }

    $record.phase = "runtime_replacement"
    if (Test-Path -LiteralPath $runtimePath) {
        Invoke-WithRetry { [IO.Directory]::Move($runtimePath, $backupPath) } "runtime-directory" $record
        $backupCreated = $true
    }
    Invoke-WithRetry { [IO.Directory]::Move($stagePath, $runtimePath) } "runtime-directory" $record
    $destinationReplaced = $true
    foreach ($required in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $runtimePath $required) -PathType Leaf)) {
            throw "Required runtime file is missing after replacement: $required"
        }
    }
    if ($backupCreated -and (Test-Path -LiteralPath $backupPath)) {
        [IO.Directory]::Delete($backupPath, $true)
    }
    Remove-Item -LiteralPath $PayloadArchivePath -Force
    Remove-Item -LiteralPath $PayloadMetadataPath -Force
    $record.phase = "completed"
    $record.status = "succeeded"
    $record.final_outcome = "runtime_payload_installed"
    $record.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Record $record $attemptPath
    Write-Output "Runtime payload installed successfully."
    exit 0
} catch {
    if ($zip) { $zip.Dispose() }
    if ($destinationReplaced -and (Test-Path -LiteralPath $runtimePath)) {
        Remove-Item -LiteralPath $runtimePath -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($backupCreated -and (Test-Path -LiteralPath $backupPath) -and -not (Test-Path -LiteralPath $runtimePath)) {
        try { [IO.Directory]::Move($backupPath, $runtimePath) } catch { }
    }
    if (Test-Path -LiteralPath $stagePath) {
        Remove-Item -LiteralPath $stagePath -Recurse -Force -ErrorAction SilentlyContinue
    }
    $code = Get-Win32ErrorCode $_
    $record.status = "failed"
    $record.final_outcome = "installation_failed"
    $record.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    $record.windows_error_code = $code
    $record.windows_error_category = Get-ErrorCategory $code $_
    $record.windows_error_message = $_.Exception.Message
    Write-Record $record $attemptPath
    Write-Output "Runtime payload installation failed: $($record.windows_error_category) code=$code"
    exit 1
}
