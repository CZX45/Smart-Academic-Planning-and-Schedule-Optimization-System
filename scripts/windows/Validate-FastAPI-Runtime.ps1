[CmdletBinding()]
param(
    [string]$RuntimeRoot = "dist\local-desktop-api\sapsos-api"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$root = Get-Item -LiteralPath (Join-Path $repoRoot $RuntimeRoot) -Force -ErrorAction Stop
$executable = Join-Path $root.FullName "sapsos-api.exe"
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Packaged FastAPI executable is missing: $executable"
}
if ((Get-Item -LiteralPath $executable).Length -le 0) {
    throw "Packaged FastAPI executable is empty: $executable"
}
if (-not (Test-Path -LiteralPath (Join-Path $root.FullName "app") -PathType Container)) {
    throw "Packaged FastAPI application resources are missing."
}
Write-Output "Validated packaged FastAPI runtime: $($root.FullName)"
