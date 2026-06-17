param(
	[string]$StartPath = ".",
	[int]$MaxFilesPerType = 120
)

$ErrorActionPreference = "Stop"

function Find-ProjectRoot {
	param([string]$Path)

	$current = Resolve-Path -LiteralPath $Path
	$item = Get-Item -LiteralPath $current
	if (-not $item.PSIsContainer) {
		$current = $item.DirectoryName
	}

	while ($current) {
		if (Test-Path -LiteralPath (Join-Path $current "project.godot")) {
			return $current
		}
		$parent = Split-Path -Parent $current
		if ($parent -eq $current) {
			break
		}
		$current = $parent
	}

	throw "No project.godot found from $Path upward."
}

$root = Find-ProjectRoot -Path $StartPath
$projectFile = Join-Path $root "project.godot"

Write-Output "ProjectRoot: $root"
Write-Output "ProjectFile: $projectFile"
Write-Output ""

$projectText = Get-Content -LiteralPath $projectFile
$inAutoload = $false
$autoloads = @()
foreach ($line in $projectText) {
	if ($line -match "^\[autoload\]") {
		$inAutoload = $true
		continue
	}
	if ($line -match "^\[.+\]") {
		$inAutoload = $false
	}
	if ($inAutoload -and $line -match "=") {
		$autoloads += $line.Trim()
	}
}

if ($autoloads.Count -gt 0) {
	Write-Output "Autoloads:"
	$autoloads | ForEach-Object { Write-Output "  $_" }
	Write-Output ""
}

$extensions = @("*.gd", "*.tscn", "*.tres", "*.res", "*.gdshader")
foreach ($extension in $extensions) {
	$files = Get-ChildItem -LiteralPath $root -Recurse -File -Filter $extension |
		Where-Object { $_.FullName -notmatch "\\.godot\\" } |
		Sort-Object FullName

	Write-Output "$extension files: $($files.Count)"
	$files |
		Select-Object -First $MaxFilesPerType |
		ForEach-Object {
			$relative = $_.FullName.Substring($root.Length).TrimStart("\")
			Write-Output "  $relative"
		}
	if ($files.Count -gt $MaxFilesPerType) {
		Write-Output "  ... $($files.Count - $MaxFilesPerType) more"
	}
	Write-Output ""
}
