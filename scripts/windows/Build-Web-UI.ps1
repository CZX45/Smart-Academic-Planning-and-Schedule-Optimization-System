[CmdletBinding()]
param(
    [string]$OutputRoot = "dist\local-desktop-web"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$webRoot = Join-Path $repoRoot "apps\web"
$nextOutput = Join-Path $webRoot "out"
$outputPath = Join-Path $repoRoot $OutputRoot

if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    throw "The developer build tool 'corepack' was not found. Install Node.js/Corepack for builds; the packaged runtime does not require Node.js."
}

$start = Get-Date
Push-Location $repoRoot
try {
    $env:NEXT_TELEMETRY_DISABLED = "1"
    & corepack pnpm --filter @sapsos/web build
    if ($LASTEXITCODE -ne 0) {
        throw "The static Web UI build failed."
    }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath (Join-Path $nextOutput "index.html"))) {
    throw "The static Web UI build did not produce '$nextOutput\index.html'."
}

if (Test-Path -LiteralPath $outputPath) {
    Remove-Item -LiteralPath $outputPath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
Copy-Item -Path (Join-Path $nextOutput "*") -Destination $outputPath -Recurse -Force

$commit = (& git -C $repoRoot rev-parse HEAD).Trim()
$files = @(Get-ChildItem -LiteralPath $outputPath -Recurse -File)
$bytes = ($files | Measure-Object -Property Length -Sum).Sum
@(
    "commit=$commit"
    "strategy=next-static-export"
    "file_count=$($files.Count)"
    "byte_count=$bytes"
    "runtime_api_bridge=query:api_base_url"
) | Set-Content -LiteralPath (Join-Path $outputPath "build-manifest.txt") -Encoding UTF8

Write-Output "Web UI artifact: $outputPath"
Write-Output "Files: $($files.Count)"
Write-Output "Bytes: $bytes"
Write-Output "DurationSeconds: $([math]::Round(((Get-Date) - $start).TotalSeconds, 2))"
