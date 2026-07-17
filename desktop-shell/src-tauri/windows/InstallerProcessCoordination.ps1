[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallRoot,
    [int]$TimeoutSeconds = 20,
    [switch]$TestMode
)

$ErrorActionPreference = "Stop"
$ciTestMode = $env:CI -eq "true" -and $env:SAPSOS_LIFECYCLE_TEST_MODE -eq "true"
$localAppData = if ($TestMode -and $ciTestMode) { $env:LOCALAPPDATA } else { [Environment]::GetFolderPath("LocalApplicationData") }
$expectedRoot = Join-Path $localAppData "Programs\SAPSOS Local Desktop"
$resolvedRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\', '/')
if ($resolvedRoot -ne ([IO.Path]::GetFullPath($expectedRoot).TrimEnd('\', '/'))) {
    throw "Installer path is not the stable per-user install directory."
}
$appPath = [IO.Path]::GetFullPath((Join-Path $resolvedRoot "sapsos-local-desktop.exe"))
$apiPath = [IO.Path]::GetFullPath((Join-Path $resolvedRoot "runtime\sapsos-api\sapsos-api.exe"))

function Get-ExactProcess([string]$PathValue) {
    $normalized = [IO.Path]::GetFullPath($PathValue)
    @(Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and
        ([IO.Path]::GetFullPath($_.ExecutablePath) -eq $normalized)
    })
}

function Wait-ForExit([int]$ProcessId, [int]$Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (-not (Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue)) { return $true }
        Start-Sleep -Milliseconds 200
    }
    return $false
}

$appProcesses = @(Get-ExactProcess $appPath)
if ($appProcesses.Count -eq 0) {
    Write-Output "No installed SAPSOS desktop process is running."
    exit 0
}
foreach ($app in $appProcesses) {
    $apiProcesses = @(Get-ExactProcess $apiPath | Where-Object { [int]$_.ParentProcessId -eq [int]$app.ProcessId })
    $process = Get-Process -Id ([int]$app.ProcessId) -ErrorAction SilentlyContinue
    if ($process -and $process.MainWindowHandle -ne 0) {
        [void]$process.CloseMainWindow()
    }
    if (-not (Wait-ForExit ([int]$app.ProcessId) $TimeoutSeconds)) {
        throw "SAPSOS is still running. Close the application before continuing."
    }
    foreach ($api in $apiProcesses) {
        if (-not (Wait-ForExit ([int]$api.ProcessId) 2)) {
            $apiProcess = Get-Process -Id ([int]$api.ProcessId) -ErrorAction SilentlyContinue
            if ($apiProcess) { $apiProcess.Kill() }
            if (-not (Wait-ForExit ([int]$api.ProcessId) 3)) {
                throw "The SAPSOS local runtime did not exit safely."
            }
        }
    }
}
Write-Output "SAPSOS installed process coordination completed."
