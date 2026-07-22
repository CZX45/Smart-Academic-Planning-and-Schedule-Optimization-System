[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallRoot,
    [string]$InstallerVersion = "",
    # Tauri waits up to 30 seconds for a trusted packaged API descendant during
    # shutdown; leave bounded headroom so a closed window is not misreported as
    # a still-running desktop instance.
    [int]$TimeoutSeconds = 45,
    [switch]$TestMode,
    [string]$DiagnosticDirectory = ""
)

$ErrorActionPreference = "Stop"
$exitCodes = [ordered]@{
    Success = 0
    RealRunningProcess = 10
    InvalidInstallRoot = 20
    ProcessInspectionError = 30
    InternalError = 40
}
$ciTestMode = $env:CI -eq "true" -and $env:SAPSOS_LIFECYCLE_TEST_MODE -eq "true"
$localAppData = if ($TestMode -and $ciTestMode) { $env:LOCALAPPDATA } else { [Environment]::GetFolderPath("LocalApplicationData") }
$expectedRoot = Join-Path $localAppData "Programs\SAPSOS Local Desktop"
$expectedRoot = [IO.Path]::GetFullPath($expectedRoot).TrimEnd('\', '/')
$resolvedRoot = $null
$allProcesses = @()
try {
    $diagnosticDirectory = if ($DiagnosticDirectory) {
        [IO.Path]::GetFullPath($DiagnosticDirectory)
    } else {
        Join-Path ([IO.Path]::GetTempPath()) "SAPSOS\installer-preflight"
    }
} catch {
    $diagnosticDirectory = Join-Path ([IO.Path]::GetTempPath()) "SAPSOS\installer-preflight"
}

function Write-PreflightDiagnostic(
    [string]$Category,
    [int]$ExitCode,
    [string]$Message,
    [int]$ProcessCount = -1,
    [object[]]$Candidates = @()
) {
    $candidateRecords = @($Candidates | ForEach-Object {
        [ordered]@{
            pid = if ($_.ProcessId) { [int]$_.ProcessId } else { $null }
            path = $_.ExecutablePath
        }
    })
    $record = [ordered]@{
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
        installer_version = $InstallerVersion
        category = $Category
        exit_code = $ExitCode
        message = $Message
        expected_root = $expectedRoot
        received_root = $InstallRoot
        normalized_received_root = $resolvedRoot
        process_count = $ProcessCount
        trusted_candidates = $candidateRecords
    }
    try {
        New-Item -ItemType Directory -Force -Path $diagnosticDirectory | Out-Null
        $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmssfff")
        $path = Join-Path $diagnosticDirectory "preflight-$stamp-$ExitCode.json"
        $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding UTF8
        Write-Output "Preflight diagnostic written: $path"
    } catch {
        Write-Output "Preflight diagnostic persistence unavailable."
    }
}

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $message = "Installer path is empty; expected the stable per-user install directory."
    Write-Output $message
    Write-PreflightDiagnostic "INVALID_INSTALL_ROOT" $exitCodes.InvalidInstallRoot $message
    exit $exitCodes.InvalidInstallRoot
}
try {
    $resolvedRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\', '/')
} catch {
    $message = "Installer path could not be normalized."
    Write-Output $message
    Write-PreflightDiagnostic "INVALID_INSTALL_ROOT" $exitCodes.InvalidInstallRoot $message
    exit $exitCodes.InvalidInstallRoot
}
if (-not [StringComparer]::OrdinalIgnoreCase.Equals($resolvedRoot, $expectedRoot)) {
    $message = "Installer path is not the stable per-user install directory."
    Write-Output $message
    Write-PreflightDiagnostic "INVALID_INSTALL_ROOT" $exitCodes.InvalidInstallRoot $message
    exit $exitCodes.InvalidInstallRoot
}
$appPath = [IO.Path]::GetFullPath((Join-Path $resolvedRoot "sapsos-local-desktop.exe"))
$apiPath = [IO.Path]::GetFullPath((Join-Path $resolvedRoot "runtime\sapsos-api\sapsos-api.exe"))
$runtimeManifestPath = Join-Path $localAppData "SAPSOS\runtime.json"

function Get-ExactProcess([string]$PathValue) {
    $normalized = [IO.Path]::GetFullPath($PathValue)
    try {
        return @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
            $_.ExecutablePath -and
            ([IO.Path]::GetFullPath($_.ExecutablePath) -eq $normalized)
        })
    } catch {
        Write-Output "CIM process enumeration was unavailable; using exact-path process fallback."
        $matches = @()
        foreach ($candidate in @(Get-Process -ErrorAction SilentlyContinue)) {
            try {
                if ($candidate.Path -and [IO.Path]::GetFullPath($candidate.Path) -eq $normalized) {
                    $matches += [pscustomobject]@{
                        ProcessId = $candidate.Id
                        ExecutablePath = $candidate.Path
                        ParentProcessId = $null
                    }
                }
            } catch { continue }
        }
        return $matches
    }
}

function Wait-ForExit([int]$ProcessId, [int]$Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (-not (Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue)) { return $true }
        Start-Sleep -Milliseconds 200
    }
    return $false
}

function Get-ProcessDescendants([int]$RootPid, [object[]]$Processes) {
    $descendants = @()
    $frontier = @($RootPid)
    while ($frontier.Count -gt 0) {
        $parents = @($frontier)
        $frontier = @()
        foreach ($candidate in $Processes) {
            if ($candidate.ParentProcessId -and ($parents -contains [int]$candidate.ParentProcessId)) {
                if (-not ($descendants | Where-Object { $_.ProcessId -eq $candidate.ProcessId })) {
                    $descendants += $candidate
                    $frontier += [int]$candidate.ProcessId
                }
            }
        }
    }
    return $descendants
}

function Get-RuntimeManifestSummary([int[]]$DescendantIds) {
    if (-not (Test-Path -LiteralPath $runtimeManifestPath -PathType Leaf)) {
        return "missing"
    }
    try {
        $manifest = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json
        $manifestPid = [int]$manifest.pid
        $process = @($allProcesses | Where-Object { [int]$_.ProcessId -eq $manifestPid }) | Select-Object -First 1
        if (-not $process) {
            return "pid=$manifestPid status=$($manifest.status) stale=dead"
        }
        $processPath = [IO.Path]::GetFullPath($process.ExecutablePath)
        if ($processPath -ne $apiPath) {
            return "pid=$manifestPid status=$($manifest.status) stale=path-mismatch path=$processPath"
        }
        $ownership = if ($DescendantIds -contains $manifestPid) { "desktop-descendant" } else { "not-desktop-descendant" }
        return "pid=$manifestPid status=$($manifest.status) ownership=$ownership"
    } catch {
        return "invalid"
    }
}

try {
    $allProcesses = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.ExecutablePath
    })
} catch {
    $processTreeError = $_.Exception.Message
    Write-Output "CIM process tree enumeration was unavailable; descendant cleanup is disabled."
}

try {
    $appProcesses = @(Get-ExactProcess $appPath | Where-Object {
        $_ -and $_.ProcessId -and $_.ExecutablePath
    })
    if ($appProcesses.Count -eq 0) {
        Write-Output "No installed SAPSOS desktop process is running."
        exit $exitCodes.Success
    }
    if ($processTreeError) {
        $message = "Trusted process ancestry could not be inspected: $processTreeError"
        Write-PreflightDiagnostic "PROCESS_INSPECTION_ERROR" $exitCodes.ProcessInspectionError $message $allProcesses.Count @($appProcesses)
        exit $exitCodes.ProcessInspectionError
    }
    foreach ($app in $appProcesses) {
        $descendantProcesses = @(Get-ProcessDescendants ([int]$app.ProcessId) $allProcesses)
        $descendantIds = @($descendantProcesses | ForEach-Object { [int]$_.ProcessId })
        $apiProcesses = @(
            Get-ExactProcess $apiPath | Where-Object {
                $_ -and $_.ProcessId -and $_.ExecutablePath -and
                ($descendantIds -contains [int]$_.ProcessId)
            }
        )
        $parentPid = if ($app.ParentProcessId) { [int]$app.ParentProcessId } else { "unknown" }
        $windowHandle = (Get-Process -Id ([int]$app.ProcessId) -ErrorAction SilentlyContinue).MainWindowHandle
        Write-Output "Exact SAPSOS desktop process detected: pid=$($app.ProcessId) parent_pid=$parentPid window_handle=$windowHandle path=$($app.ExecutablePath) runtime_manifest=$(Get-RuntimeManifestSummary $descendantIds)"
        $process = Get-Process -Id ([int]$app.ProcessId) -ErrorAction SilentlyContinue
        if ($process -and $process.MainWindowHandle -ne 0) { [void]$process.CloseMainWindow() }
        if (-not (Wait-ForExit ([int]$app.ProcessId) $TimeoutSeconds)) {
            if ($ciTestMode -and $process) {
                Write-Output "CI test mode: terminating exact-path desktop PID $($app.ProcessId)."
                Stop-Process -Id ([int]$app.ProcessId) -Force -ErrorAction Stop
                if (-not (Wait-ForExit ([int]$app.ProcessId) 3)) { throw "The exact SAPSOS desktop process did not exit safely." }
            } else {
                $message = "SAPSOS exact desktop process is still running: pid=$($app.ProcessId) parent_pid=$parentPid path=$($app.ExecutablePath) runtime_manifest=$(Get-RuntimeManifestSummary $descendantIds). Close the application before continuing."
                Write-PreflightDiagnostic "REAL_RUNNING_PROCESS" $exitCodes.RealRunningProcess $message $allProcesses.Count @($app)
                exit $exitCodes.RealRunningProcess
            }
        }
        foreach ($api in @($apiProcesses | Sort-Object ProcessId -Unique)) {
            if (-not (Wait-ForExit ([int]$api.ProcessId) 2)) {
                $apiProcess = Get-Process -Id ([int]$api.ProcessId) -ErrorAction SilentlyContinue
                if ($ciTestMode -and $apiProcess) {
                    Write-Output "CI test mode: terminating exact-path API child PID $($api.ProcessId)."
                    $apiProcess.Kill()
                    if (-not (Wait-ForExit ([int]$api.ProcessId) 3)) { throw "The SAPSOS local runtime did not exit safely." }
                } else {
                    $message = "The SAPSOS local runtime did not exit safely: pid=$($api.ProcessId) path=$($api.ExecutablePath)."
                    Write-PreflightDiagnostic "REAL_RUNNING_PROCESS" $exitCodes.RealRunningProcess $message $allProcesses.Count @($api)
                    exit $exitCodes.RealRunningProcess
                }
            }
        }
    }
} catch {
    $message = "Installer process coordination failed internally."
    Write-Output "$message $($_.Exception.Message)"
    Write-PreflightDiagnostic "INTERNAL_ERROR" $exitCodes.InternalError $message $allProcesses.Count
    exit $exitCodes.InternalError
}
Write-Output "SAPSOS installed process coordination completed."
