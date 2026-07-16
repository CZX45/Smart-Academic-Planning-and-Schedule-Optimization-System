[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$identity = Get-Content (Join-Path $repoRoot "desktop-shell\desktop-identity.json") -Raw | ConvertFrom-Json
$tauri = Get-Content (Join-Path $repoRoot "desktop-shell\src-tauri\tauri.conf.json") -Raw | ConvertFrom-Json
$cargo = Get-Content (Join-Path $repoRoot "desktop-shell\src-tauri\Cargo.toml") -Raw
$apiConfig = Get-Content (Join-Path $repoRoot "apps\api\app\config.py") -Raw

function Assert-Equal([string]$label, [string]$expected, [string]$actual) {
    if ($expected -ne $actual) { throw "$label drift: expected '$expected', found '$actual'." }
}

Assert-Equal "product name" $identity.product_name $tauri.productName
Assert-Equal "bundle identifier" $identity.bundle_identifier $tauri.identifier
Assert-Equal "Windows application identifier" $identity.bundle_identifier $identity.windows_application_id
Assert-Equal "version" $identity.version $tauri.version
Assert-Equal "publisher" $identity.publisher $tauri.bundle.publisher
Assert-Equal "Cargo package name" "sapsos-local-desktop" (([regex]::Match($cargo, '(?m)^name\s*=\s*"([^"]+)"$')).Groups[1].Value)
Assert-Equal "Cargo version" $identity.version (([regex]::Match($cargo, '(?m)^version\s*=\s*"([^"]+)"$')).Groups[1].Value)
Assert-Equal "executable name" "sapsos-local-desktop.exe" $identity.executable_name
if ($identity.installer_artifact_name -ne "SAPSOS-Local-Desktop-{version}-x64-setup.exe") {
    throw "Installer artifact naming convention drifted."
}

foreach ($packagePath in @(
        "apps\api\package.json",
        "apps\web\package.json",
        "apps\extension\package.json",
        "packages\shared\package.json",
        "packages\config\package.json"
    )) {
    $package = Get-Content (Join-Path $repoRoot $packagePath) -Raw | ConvertFrom-Json
    Assert-Equal "$packagePath version" $identity.version $package.version
}
$pythonProject = Get-Content (Join-Path $repoRoot "apps\api\pyproject.toml") -Raw
Assert-Equal "Python API version" $identity.version (([regex]::Match($pythonProject, '(?m)^version\s*=\s*"([^"]+)"\r?$')).Groups[1].Value)

$appId = (([regex]::Match($apiConfig, '(?m)^APP_ID\s*=\s*"([^"]+)"\r?$')).Groups[1].Value)
$dataDir = (([regex]::Match($apiConfig, '(?m)^APP_DATA_DIR_NAME\s*=\s*"([^"]+)"\r?$')).Groups[1].Value)
Assert-Equal "API app id" $identity.bundle_identifier $appId
Assert-Equal "API data directory" $identity.app_data_directory $dataDir

if ($tauri.bundle.targets -join "," -ne "nsis") { throw "Windows packaging must use exactly one target: nsis." }
if ($tauri.bundle.windows.nsis.installMode -ne "currentUser") { throw "Windows installer must remain per-user/currentUser." }
if (-not $tauri.bundle.resources.PSObject.Properties.Name.Contains("../../dist/local-desktop-api/sapsos-api/**/*")) { throw "Tauri API runtime resource mapping is missing." }
if ($identity.install_scope -ne "per-user") { throw "Identity install scope must be per-user." }

Write-Output "Desktop identity is consistent: $($identity.product_name) $($identity.version)"
