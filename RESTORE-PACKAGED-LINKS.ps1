# Recreate packaged Node dependency junctions after Windows ZIP extraction.
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($PSScriptRoot)
$prefix = $root.TrimEnd('\') + '\'
$links = Get-Content -LiteralPath (Join-Path $root 'PACKAGED-LINKS.json') -Raw | ConvertFrom-Json
foreach ($link in $links) {
    if (-not $link.internal -or -not $link.directory) { continue }
    $path = [IO.Path]::GetFullPath((Join-Path $root $link.path))
    $target = [IO.Path]::GetFullPath((Join-Path $root $link.target))
    if (-not $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not $target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'A packaged link leaves the project folder.'
    }
    if (Test-Path -LiteralPath $path) {
        $existing = Get-Item -LiteralPath $path -Force
        if ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        throw "Cannot restore a link over an existing file or folder: $path. Use a fresh extraction or run pnpm install in frontend."
    }
    if (-not (Test-Path -LiteralPath $target -PathType Container)) { throw "Missing packaged dependency: $target" }
    New-Item -ItemType Junction -Path $path -Target $target | Out-Null
}
Write-Host 'Packaged dependency links restored. Virtual environments may still need recreation on another computer.'
