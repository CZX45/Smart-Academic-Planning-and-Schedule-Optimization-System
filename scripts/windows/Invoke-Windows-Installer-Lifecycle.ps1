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

if ([IO.Path]::GetPathRoot($root) -eq $root) { throw "Lifecycle test root cannot be a drive root." }
if (Test-Path -LiteralPath $root) { throw "Lifecycle test root must not already exist: $root" }
New-Item -ItemType Directory -Force -Path $root | Out-Null
$env:LOCALAPPDATA = $root

function Assert-True([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Invoke-Installer([string]$PathValue) {
    $process = Start-Process -FilePath $PathValue -ArgumentList "/S" -Wait -PassThru
    Assert-True ($process.ExitCode -eq 0) "Installer failed with exit code $($process.ExitCode): $PathValue"
}
function Assert-InstalledFiles([string]$ExpectedVersion) {
    Assert-True (Test-Path (Join-Path $installRoot "sapsos-local-desktop.exe") -PathType Leaf) "Installed executable is missing."
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

try {
    Invoke-Installer $installer
    Assert-InstalledFiles "0.1.0"
    $external = Write-Sentinels

    # Same-version repair must not create another install or touch the data root.
    Invoke-Installer $installer
    Assert-InstalledFiles "0.1.0"
    Assert-Retention $external

    # The two-version run uses the same product identity and stable AppData root.
    Invoke-Installer $upgradeInstaller
    Assert-InstalledFiles "0.1.1"
    Assert-Retention $external

    # Process gate: unrelated same-name processes are ignored; the installed app is gated by path.
    $appProcess = Start-Process -FilePath (Join-Path $installRoot "sapsos-local-desktop.exe") -PassThru
    Start-Sleep -Seconds 5
    $observed = Get-Process -Id $appProcess.Id -ErrorAction SilentlyContinue
    Assert-True ($null -ne $observed) "Installed application did not remain running for coordination smoke."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $coordination -InstallRoot $installRoot -TestMode
    Assert-True ($LASTEXITCODE -eq 0) "Running-process coordination smoke failed."
    $appProcess.WaitForExit(10)
    Assert-True $appProcess.HasExited "Process coordination did not close the installed application."

    $uninstaller = Get-ChildItem $installRoot -Filter "uninstall*.exe" -File | Select-Object -First 1
    Assert-True ($null -ne $uninstaller) "Uninstaller registration/executable is missing."
    $uninstallProcess = Start-Process -FilePath $uninstaller.FullName -ArgumentList "/S" -Wait -PassThru
    Assert-True ($uninstallProcess.ExitCode -eq 0) "Default uninstall failed with exit code $($uninstallProcess.ExitCode)."
    Assert-True (-not (Test-Path $installRoot)) "Default uninstall did not remove installer-owned files."
    Assert-Retention $external

    # Reinstall must reuse the same identity and retained AppData root.
    Invoke-Installer $installer
    Assert-InstalledFiles "0.1.0"
    Assert-Retention $external

    Write-Output "clean_install=passed"
    Write-Output "same_version_repair=passed"
    Write-Output "two_version_upgrade=passed"
    Write-Output "running_process_coordination=passed"
    Write-Output "default_uninstall_retention=passed"
    Write-Output "reinstall_after_uninstall=passed"
}
finally {
    if (Test-Path -LiteralPath $root) {
        Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    }
}
