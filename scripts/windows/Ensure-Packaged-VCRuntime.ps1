[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RuntimeRoot,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$requiredHostModules = @(
    "Microsoft.PowerShell.Security",
    "Microsoft.PowerShell.Utility"
)
foreach ($moduleName in $requiredHostModules) {
    $modulePath = Join-Path $PSHOME "Modules\$moduleName\$moduleName.psd1"
    if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
        throw "The current PowerShell host is missing a required module: $modulePath"
    }
    Import-Module -Name $modulePath -ErrorAction Stop
}
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$apiRoot = Join-Path $repoRoot "apps\api"
$resolvedRuntimeRoot = [IO.Path]::GetFullPath($RuntimeRoot)
if (-not (Test-Path -LiteralPath $resolvedRuntimeRoot -PathType Container)) {
    throw "Packaged runtime root does not exist: $resolvedRuntimeRoot"
}
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "Python build tool '$Python' was not found while locating MSVCP140.dll."
}

function Assert-TrustedVCRuntime([string]$PathValue) {
    $runtime = Get-Item -LiteralPath $PathValue -Force -ErrorAction Stop
    if ($runtime.Length -le 0) {
        throw "Microsoft VC runtime is empty: $($runtime.FullName)"
    }
    if ($runtime.VersionInfo.CompanyName -ne "Microsoft Corporation") {
        throw "VC runtime publisher metadata is not Microsoft Corporation: $($runtime.FullName)"
    }
    $signature = Microsoft.PowerShell.Security\Get-AuthenticodeSignature -LiteralPath $runtime.FullName
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        throw "VC runtime Authenticode signature is not valid: $($runtime.FullName) [$($signature.Status)]"
    }

    $stream = [IO.File]::Open($runtime.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $reader = [IO.BinaryReader]::new($stream)
    try {
        if ($reader.ReadUInt16() -ne 0x5A4D) {
            throw "VC runtime is not a PE executable: $($runtime.FullName)"
        }
        $stream.Position = 0x3C
        $peOffset = $reader.ReadInt32()
        $stream.Position = $peOffset
        if ($reader.ReadUInt32() -ne 0x00004550) {
            throw "VC runtime has an invalid PE signature: $($runtime.FullName)"
        }
        if ($reader.ReadUInt16() -ne 0x8664) {
            throw "VC runtime is not x64: $($runtime.FullName)"
        }
    } finally {
        $reader.Dispose()
        $stream.Dispose()
    }
    return $runtime
}

$target = Join-Path $resolvedRuntimeRoot "MSVCP140.dll"
if (Test-Path -LiteralPath $target -PathType Leaf) {
    $validated = Assert-TrustedVCRuntime $target
    Write-Output "Validated PyInstaller VC runtime: $($validated.FullName)"
    exit 0
}

Push-Location $apiRoot
try {
    $resolverOutput = @(& $Python -m build_support.vc_runtime 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not locate a trusted x64 MSVCP140.dll. $($resolverOutput -join ' ')"
    }
} finally {
    Pop-Location
}
$sourcePath = @($resolverOutput | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })[-1]
$source = Assert-TrustedVCRuntime $sourcePath
Copy-Item -LiteralPath $source.FullName -Destination $target
$staged = Assert-TrustedVCRuntime $target
if ((Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash -ne
    (Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $staged.FullName -Algorithm SHA256).Hash) {
    throw "Staged VC runtime hash does not match its trusted source."
}
Write-Output "Staged trusted x64 VC runtime: $($source.FullName) -> $($staged.FullName)"
