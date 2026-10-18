[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ApiRoot,
    [Parameter(Mandatory = $true)]
    [string]$WebRoot,
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$distRoot = (Get-Item -LiteralPath (Join-Path $repoRoot "dist") -Force).FullName

function Get-CheckedRoot([string]$PathValue, [string]$Label) {
    $item = Get-Item -LiteralPath $PathValue -Force -ErrorAction Stop
    if (-not $item.PSIsContainer) { throw "$Label is not a directory: $PathValue" }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label must not be a symlink or reparse point: $PathValue"
    }
    $full = $item.FullName.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $prefix = "$distRoot$([IO.Path]::DirectorySeparatorChar)"
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label is outside the repository dist root: $full"
    }
    return $item
}

function Get-RelativePath([string]$Root, [string]$PathValue) {
    $rootUri = [Uri]::new((Resolve-Path $Root).Path.TrimEnd('\', '/') + '\')
    $pathUri = [Uri]::new((Resolve-Path $PathValue).Path)
    return [Uri]::UnescapeDataString($rootUri.MakeRelativeUri($pathUri).ToString()).Replace('\', '/')
}

function Get-Sha256([string]$PathValue) {
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $sha256.ComputeHash([IO.File]::ReadAllBytes($PathValue))
        return ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

$api = Get-CheckedRoot $ApiRoot "Packaged API root"
$web = Get-CheckedRoot $WebRoot "Static Web root"
$forbiddenPath = '(?i)(^|[\\/])(?:\.env(?:\.|$)|.*\.(?:db|sqlite|sapsos-backup)$|pairing\.json$|runtime\.json$|pending-restore\.json$|.*diagnostics.*\.(?:zip|json)$|.*backup.*\.(?:zip|sapsos-backup)$|migration-safety(?:[\\/]|$)|tests?(?:[\\/]|$)|fixtures(?:[\\/]|$)|node_modules(?:[\\/]|$)|credentials?(?:[\\/]|$)|tokens?(?:[\\/]|$))'
$base64Literal = '(?i)data:[^,\r\n]{0,80};base64,|(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{256,}={0,2}(?![A-Za-z0-9+/])'
$records = [ordered]@{}

foreach ($component in @(@{ Name = "fastapi_runtime"; Root = $api }, @{ Name = "static_web"; Root = $web })) {
    $files = @(Get-ChildItem -LiteralPath $component.Root.FullName -Recurse -Force -File)
    if ($files.Count -eq 0) { throw "$($component.Name) staging root is empty." }
    $componentRelativeRoot = Get-RelativePath $repoRoot $component.Root.FullName
    $componentRecords = @(
        foreach ($file in $files) {
            $relative = Get-RelativePath $component.Root.FullName $file.FullName
            $normalized = "$componentRelativeRoot/$relative"
            if ($normalized -match $forbiddenPath) { throw "Forbidden packaged file: $normalized" }
            if ($file.Extension -ieq ".map") { throw "Source maps require explicit security review: $normalized" }
            if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse point in packaging staging: $normalized" }
            if ($file.Length -gt 0 -and $file.Extension -match '(?i)\.(?:js|mjs|cjs|json|txt|html|css|py|toml|yaml|yml)$') {
                $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop
                if ($text -match $base64Literal) { throw "Base64 literal detected in packaged text: $normalized" }
            }
            [ordered]@{
                path = $normalized
                bytes = $file.Length
                sha256 = Get-Sha256 $file.FullName
            }
        }
    )
    $records[$component.Name] = $componentRecords
}

$manifest = [ordered]@{
    schema_version = 1
    commit = (& git -C $repoRoot rev-parse HEAD).Trim()
    product_mode = "LOCAL_DESKTOP"
    source_maps_included = $false
    components = $records
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
Write-Output "Validated packaging staging and wrote manifest: $ManifestPath"
