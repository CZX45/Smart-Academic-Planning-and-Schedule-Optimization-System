[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath,
    [Parameter(Mandatory = $true)]
    [string]$AllowedBuildRoot
)

$ErrorActionPreference = "Stop"

function Get-NormalizedPath([string]$PathValue) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        throw "Build cleanup path must not be empty."
    }
    return [IO.Path]::GetFullPath($PathValue).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
}

$allowedItem = Get-Item -LiteralPath $AllowedBuildRoot -Force -ErrorAction Stop
if (-not $allowedItem.PSIsContainer) { throw "Allowed build root is not a directory: $AllowedBuildRoot" }
if (($allowedItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "Allowed build root must not be a symlink or reparse point: $AllowedBuildRoot"
}
$allowed = Get-NormalizedPath $allowedItem.FullName
$target = Get-NormalizedPath $TargetPath

$rootOfTarget = [IO.Path]::GetPathRoot($target).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
if ($target -eq $rootOfTarget) { throw "Refusing to clean a drive root: $target" }
if ($target -eq $allowed) { throw "Refusing to clean the allowed build root itself: $target" }
$allowedPrefix = "$allowed$([IO.Path]::DirectorySeparatorChar)"
if (-not $target.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Cleanup target is outside the allowed build root: $target"
}

$sensitiveRoots = @(
    [Environment]::GetFolderPath("UserProfile"),
    [Environment]::GetFolderPath("LocalApplicationData"),
    [Environment]::GetFolderPath("ApplicationData")
) | Where-Object { $_ }
foreach ($sensitiveRoot in $sensitiveRoots) {
    $normalizedSensitiveRoot = Get-NormalizedPath $sensitiveRoot
    if ($target -eq $normalizedSensitiveRoot -or $target.StartsWith("$normalizedSensitiveRoot$([IO.Path]::DirectorySeparatorChar)", [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean a user or AppData path: $target"
    }
}

$cursor = $target
while ($cursor.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    if (Test-Path -LiteralPath $cursor) {
        $item = Get-Item -LiteralPath $cursor -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing to traverse a symlink or reparse point: $cursor"
        }
    }
    $parent = Split-Path -Parent $cursor
    if (-not $parent -or $parent -eq $cursor) { break }
    $cursor = $parent
}

if (Test-Path -LiteralPath $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
}
Write-Output "Safely cleaned build output: $target"
