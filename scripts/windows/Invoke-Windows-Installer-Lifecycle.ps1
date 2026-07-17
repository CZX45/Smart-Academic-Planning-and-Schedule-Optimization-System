[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallerPath,
    [Parameter(Mandatory = $true)][string]$UpgradeInstallerPath,
    [string]$TestRoot = (Join-Path ([IO.Path]::GetTempPath()) "SAPSOS-installer-lifecycle-$([Guid]::NewGuid().ToString('N'))")
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..\..")).Path
$coordination = Join-Path $repoRoot "desktop-shell\src-tauri\windows\InstallerProcessCoordination.ps1"
$installer = (Resolve-Path $InstallerPath).Path
$upgradeInstaller = (Resolve-Path $UpgradeInstallerPath).Path
$root = [IO.Path]::GetFullPath($TestRoot).TrimEnd('\', '/')
$installRoot = Join-Path $root "Programs\SAPSOS Local Desktop"
$dataRoot = Join-Path $root "SAPSOS"
$startMenu = Join-Path $root "Microsoft\Windows\Start Menu\Programs\SAPSOS Local Desktop\SAPSOS Local Desktop.lnk"
$phase = "initialization"
$processTimeoutSeconds = 180

if ([IO.Path]::GetPathRoot($root) -eq $root) { throw "Lifecycle test root cannot be a drive root." }
if (Test-Path -LiteralPath $root) { throw "Lifecycle test root must not already exist: $root" }
New-Item -ItemType Directory -Force -Path $root | Out-Null
$env:LOCALAPPDATA = $root

function Write-Phase([string]$Name, [ValidateSet("starting", "completed", "failed")][string]$Status, [string]$Details = "") {
    $script:phase = $Name
    $suffix = if ($Details) { " $Details" } else { "" }
    Write-Host "phase=$Name status=$Status$suffix"
}
function Assert-True([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Invoke-ProcessWithTimeout([string]$PathValue, [string[]]$Arguments, [int]$TimeoutSeconds, [string]$PhaseName) {
    $process = Start-Process -FilePath $PathValue -ArgumentList $Arguments -PassThru
    Write-Host "phase=$PhaseName process_pid=$($process.Id) timeout_seconds=$TimeoutSeconds"
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while (-not $process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
    }
    if (-not $process.HasExited) {
        Write-Host "phase=$PhaseName status=timeout process_pid=$($process.Id)"
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "Lifecycle phase '$PhaseName' timed out after $TimeoutSeconds seconds."
    }
    Write-Host "phase=$PhaseName process_exit_code=$($process.ExitCode)"
    Assert-True ($process.ExitCode -eq 0) "Lifecycle phase '$PhaseName' failed with exit code $($process.ExitCode): $PathValue"
    return $process
}
function Invoke-Installer([string]$PathValue, [string]$PhaseName) {
    Write-Host "phase=$PhaseName install_root=Programs/SAPSOS Local Desktop"
    Invoke-ProcessWithTimeout $PathValue @("/S", "/D=$installRoot") $processTimeoutSeconds $PhaseName | Out-Null
}
function Assert-InstalledFiles([string]$ExpectedVersion) {
    $executable = Join-Path $installRoot "sapsos-local-desktop.exe"
    Assert-True (Test-Path $executable -PathType Leaf) "Installed executable is missing."
    $installedVersion = (Get-Item $executable).VersionInfo.ProductVersion
    Assert-True ($installedVersion -like "$ExpectedVersion*") "Installed executable version '$installedVersion' does not match expected '$ExpectedVersion'."
    Assert-True (Test-Path (Join-Path $installRoot "runtime\sapsos-api\sapsos-api.exe") -PathType Leaf) "Packaged API sidecar is missing."
    Assert-True (Test-Path (Join-Path $installRoot "index.html") -PathType Leaf) "Static Web asset is missing."
    Assert-True ((Get-ChildItem $installRoot -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '(?i)(^|-)sapsos\.db$|pairing\.json$|\.sapsos-backup$' }).Count -eq 0) "User data leaked into the install directory."
    $identity = Get-Content (Join-Path $installRoot "desktop-identity.json") -Raw -ErrorAction SilentlyContinue
    if ($identity) { Assert-True ($identity -notmatch '(?i)[A-Z]:\\Users\\') "Absolute user path leaked into install identity." }
}
function Write-Sentinels {
    New-Item -ItemType Directory -Force -Path $dataRoot, (Join-Path $dataRoot "migration-safety"), (Join-Path $dataRoot "restore-staging") | Out-Null
    "database" | Set-Content (Join-Path $dataRoot "sapsos.db")
    "backup" | Set-Content (Join-Path $dataRoot "manual-backup.sapsos-backup")
    "pairing" | Set-Content (Join-Path $dataRoot "pairing.json")
    "preference" | Set-Content (Join-Path $dataRoot "preferences.json")
    "migration" | Set-Content (Join-Path $dataRoot "migration-safety\sentinel.txt")
    "restore" | Set-Content (Join-Path $dataRoot "restore-staging\sentinel.txt")
    $external = Join-Path $root "external-backup.sapsos-backup"
    "external" | Set-Content $external
    return $external
}
function Assert-Retention([string]$ExternalPath) {
    foreach ($path in @("sapsos.db", "manual-backup.sapsos-backup", "pairing.json", "preferences.json", "migration-safety\sentinel.txt", "restore-staging\sentinel.txt")) {
        Assert-True (Test-Path (Join-Path $dataRoot $path) -PathType Leaf) "Retained sentinel is missing: $path"
    }
    Assert-True (Test-Path $ExternalPath -PathType Leaf) "External backup sentinel is missing."
}
function Stop-TestProcess([System.Diagnostics.Process]$Process) {
    if ($Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        $deadline = [DateTime]::UtcNow.AddSeconds(10)
        while (-not $Process.HasExited -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 200; $Process.Refresh() }
    }
}

try {
    Write-Host "logical_installer_version=0.1.0 logical_install_root=Programs/SAPSOS Local Desktop"
    Write-Phase "clean_install" "starting" "timeout_seconds=$processTimeoutSeconds"
    Invoke-Installer $installer "clean_install"
    Assert-InstalledFiles "0.1.0"
    Write-Phase "clean_install" "completed"
    $external = Write-Sentinels
    Write-Phase "write_sentinels" "completed"

    Write-Phase "same_version_repair" "starting" "timeout_seconds=$processTimeoutSeconds"
    Invoke-Installer $installer "same_version_repair"
    Assert-InstalledFiles "0.1.0"; Assert-Retention $external
    Write-Phase "same_version_repair" "completed"

    # The two-version upgrade intentionally reuses the stable product identity.
    Write-Host "two-version upgrade uses the same product identity."
    Write-Phase "two_version_upgrade" "starting" "timeout_seconds=$processTimeoutSeconds"
    Invoke-Installer $upgradeInstaller "two_version_upgrade"
    Assert-InstalledFiles "0.1.1"; Assert-Retention $external
    Write-Phase "two_version_upgrade" "completed"

    Write-Phase "launch_installed_app" "starting"
    $appProcess = Start-Process -FilePath (Join-Path $installRoot "sapsos-local-desktop.exe") -PassThru
    Write-Host "phase=launch_installed_app process_pid=$($appProcess.Id) timeout_seconds=30"
    Start-Sleep -Seconds 5
    Assert-True ($null -ne (Get-Process -Id $appProcess.Id -ErrorAction SilentlyContinue)) "Installed application did not remain running for coordination smoke."
    Write-Phase "launch_installed_app" "completed"

    Write-Phase "process_coordination" "starting" "timeout_seconds=30"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $coordination -InstallRoot $installRoot -TestMode
    Assert-True ($LASTEXITCODE -eq 0) "Running-process coordination smoke failed."
    $appProcess.Refresh(); Assert-True $appProcess.WaitForExit(30000) "Process coordination did not close the installed application."
    Write-Phase "process_coordination" "completed"

    $uninstaller = Get-ChildItem $installRoot -Filter "uninstall*.exe" -File | Select-Object -First 1
    Assert-True ($null -ne $uninstaller) "Uninstaller registration/executable is missing."
    Write-Phase "default_uninstall" "starting" "timeout_seconds=$processTimeoutSeconds"
    Invoke-ProcessWithTimeout $uninstaller.FullName @("/S") $processTimeoutSeconds "default_uninstall" | Out-Null
    Assert-True (-not (Test-Path $installRoot)) "Default uninstall did not remove installer-owned files."
    Write-Phase "default_uninstall" "completed"
    Assert-Retention $external; Write-Phase "retention_validation" "completed"

    Write-Phase "reinstall" "starting" "timeout_seconds=$processTimeoutSeconds"
    Invoke-Installer $installer "reinstall"
    Assert-InstalledFiles "0.1.0"; Assert-Retention $external
    Write-Phase "reinstall" "completed"
    Write-Output "clean_install=passed"; Write-Output "same_version_repair=passed"; Write-Output "two_version_upgrade=passed"; Write-Output "running_process_coordination=passed"; Write-Output "default_uninstall_retention=passed"; Write-Output "reinstall_after_uninstall=passed"
}
catch {
    Write-Phase $phase "failed" "failure_type=$($_.Exception.GetType().Name)"
    throw
}
finally {
    Write-Phase "cleanup" "starting" "timeout_seconds=10"
    if ($appProcess) { Stop-TestProcess $appProcess }
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $root) { Write-Host "phase=cleanup status=failed" } else { Write-Phase "cleanup" "completed" }
}
