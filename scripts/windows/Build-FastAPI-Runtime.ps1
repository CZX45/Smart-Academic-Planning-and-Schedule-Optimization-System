[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$OutputRoot = "dist\local-desktop-api",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$apiRoot = Join-Path $repoRoot "apps\api"
$spec = Join-Path $apiRoot "packaging\sapsos-api.spec"
$outputPath = Join-Path $repoRoot $OutputRoot
$buildPath = Join-Path $repoRoot ".cache\pyinstaller\local-desktop-api"

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "Python build tool '$Python' was not found. Install the declared developer build dependency and retry; end users do not need Python."
}

if (-not $SkipInstall) {
    & $Python -m pip install --requirement (Join-Path $apiRoot "packaging\requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Could not install the pinned PyInstaller build dependency." }
}

if (Test-Path -LiteralPath $outputPath) {
    & (Join-Path $PSScriptRoot "Invoke-SafeBuildCleanup.ps1") -TargetPath $outputPath -AllowedBuildRoot (Join-Path $repoRoot "dist")
}
if (Test-Path -LiteralPath $buildPath) {
    & (Join-Path $PSScriptRoot "Invoke-SafeBuildCleanup.ps1") -TargetPath $buildPath -AllowedBuildRoot (Join-Path $repoRoot ".cache\pyinstaller")
}
New-Item -ItemType Directory -Force -Path $outputPath, $buildPath | Out-Null

$versionFile = Join-Path $buildPath "build-version.txt"
$commit = (& git -C $repoRoot rev-parse HEAD).Trim()
Set-Content -LiteralPath $versionFile -Value "commit=$commit`nproduct_mode=LOCAL_DESKTOP`n" -Encoding UTF8

Push-Location $apiRoot
try {
    & $Python -m PyInstaller --noconfirm --clean --distpath $outputPath --workpath $buildPath $spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed to build the FastAPI runtime." }
} finally {
    Pop-Location
}

$artifact = Join-Path $outputPath "sapsos-api\sapsos-api.exe"
if (-not (Test-Path -LiteralPath $artifact)) {
    throw "Packaged FastAPI artifact was not produced at '$artifact'."
}
& (Join-Path $PSScriptRoot "Validate-FastAPI-Runtime.ps1") -RuntimeRoot (Join-Path $OutputRoot "sapsos-api")
Write-Output $artifact
