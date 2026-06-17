param(
	[string[]]$Query,
	[string]$VaultPath,
	[string]$VaultName = "Godot Codex Wiki",
	[switch]$List,
	[switch]$Overview,
	[switch]$PrintPath,
	[switch]$UseRg
)

$ErrorActionPreference = "Stop"

function Test-VaultCandidate {
	param([string]$Path)

	if ([string]::IsNullOrWhiteSpace($Path)) {
		return $false
	}
	if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
		return $false
	}

	$indexPath = Join-Path $Path "INDEX.md"
	$obsidianPath = Join-Path $Path ".obsidian"
	return (Test-Path -LiteralPath $indexPath -PathType Leaf) -and
		(Test-Path -LiteralPath $obsidianPath -PathType Container)
}

function Get-ObsidianRegistryPaths {
	$paths = @()
	if ($env:APPDATA) {
		$paths += Join-Path (Join-Path $env:APPDATA "obsidian") "obsidian.json"
	}
	if ($HOME) {
		$paths += Join-Path (Join-Path (Join-Path (Join-Path $HOME "Library") "Application Support") "obsidian") "obsidian.json"
		$paths += Join-Path (Join-Path (Join-Path $HOME ".config") "obsidian") "obsidian.json"
	}
	$paths | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -Unique
}

function Get-VaultsFromObsidianRegistry {
	foreach ($registryPath in Get-ObsidianRegistryPaths) {
		try {
			$registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
			if (-not $registry.vaults) {
				continue
			}

			foreach ($vault in $registry.vaults.PSObject.Properties.Value) {
				if ($vault.path) {
					[PSCustomObject]@{ Path = [string]$vault.path; Source = $registryPath }
				}
			}
		} catch {
			continue
		}
	}
}

function Get-CommonSearchRoots {
	$roots = @()
	if ($HOME) {
		$roots += Join-Path $HOME "Documents"
		$oneDrive = Join-Path $HOME "OneDrive"
		$roots += Join-Path $oneDrive "Documents"
		$roots += Join-Path $oneDrive "Documenten"
		$roots += Join-Path $HOME "Obsidian"
	}

	$roots |
		Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } |
		Select-Object -Unique
}

function Find-VaultByName {
	param([string]$Name)

	$candidates = @()
	foreach ($root in Get-CommonSearchRoots) {
		try {
			$candidates += Get-ChildItem -LiteralPath $root -Directory -Recurse -ErrorAction SilentlyContinue |
				Where-Object { $_.Name -eq $Name } |
				Select-Object -ExpandProperty FullName
		} catch {
			continue
		}
	}

	$candidates | Select-Object -Unique
}

function Resolve-GodotVaultPath {
	param(
		[string]$ExplicitPath,
		[string]$Name
	)

	$attempted = @()

	if ($ExplicitPath) {
		$attempted += $ExplicitPath
		if (Test-VaultCandidate -Path $ExplicitPath) {
			return (Resolve-Path -LiteralPath $ExplicitPath).ProviderPath
		}
		throw "Vault path was provided but is not a valid Godot Obsidian vault: $ExplicitPath"
	}

	$envCandidates = @(
		$env:GODOT_CODEX_VAULT,
		$env:GODOT_CODEX_VAULT_PATH,
		$env:CODEX_GODOT_VAULT
	)
	foreach ($candidate in $envCandidates) {
		if (-not $candidate) {
			continue
		}
		$attempted += $candidate
		if (Test-VaultCandidate -Path $candidate) {
			return (Resolve-Path -LiteralPath $candidate).ProviderPath
		}
	}

	$configCandidates = @()
	if ($HOME) {
		$codexDir = Join-Path $HOME ".codex"
		$configCandidates += Join-Path $codexDir "godot-codex-vault.txt"
		$configCandidates += Join-Path $codexDir "godot-codex-vault.path"
	}
	foreach ($configPath in $configCandidates) {
		if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
			continue
		}
		$candidate = (Get-Content -LiteralPath $configPath -Raw).Trim()
		if (-not $candidate) {
			continue
		}
		$attempted += "$configPath -> $candidate"
		if (Test-VaultCandidate -Path $candidate) {
			return (Resolve-Path -LiteralPath $candidate).ProviderPath
		}
	}

	$registeredVaults = @(Get-VaultsFromObsidianRegistry)
	foreach ($registeredVault in $registeredVaults) {
		$leaf = Split-Path -Leaf $registeredVault.Path
		if ($leaf -eq $Name -or $registeredVault.Path -like "*$Name*") {
			$attempted += "$($registeredVault.Source) -> $($registeredVault.Path)"
			if (Test-VaultCandidate -Path $registeredVault.Path) {
				return (Resolve-Path -LiteralPath $registeredVault.Path).ProviderPath
			}
		}
	}

	foreach ($candidate in Find-VaultByName -Name $Name) {
		$attempted += $candidate
		if (Test-VaultCandidate -Path $candidate) {
			return (Resolve-Path -LiteralPath $candidate).ProviderPath
		}
	}

	$attemptedText = if ($attempted.Count -gt 0) { $attempted -join "`n- " } else { "(no candidates found)" }
	throw "Could not find the Godot Obsidian vault. Pass -VaultPath, set GODOT_CODEX_VAULT, or add the vault to Obsidian. Candidates tried:`n- $attemptedText"
}

$VaultPath = Resolve-GodotVaultPath -ExplicitPath $VaultPath -Name $VaultName

if ($PrintPath) {
	Write-Output $VaultPath
	exit 0
}

function Get-MarkdownFiles {
	param([string]$Path)

	Get-ChildItem -LiteralPath $Path -Recurse -File -Filter "*.md" |
		Where-Object { $_.FullName -notmatch "\\.obsidian\\" }
}

function Read-NoteOverview {
	param(
		[System.IO.FileInfo]$File,
		[string]$Root
	)

	$raw = Get-Content -LiteralPath $File.FullName -Raw
	$rootFull = (Resolve-Path -LiteralPath $Root).ProviderPath.TrimEnd("\")
	$fileFull = $File.FullName
	if ($fileFull.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) {
		$relative = $fileFull.Substring($rootFull.Length).TrimStart("\")
	} else {
		$relative = $fileFull
	}
	$title = [System.IO.Path]::GetFileNameWithoutExtension($File.Name)
	$type = ""
	$status = ""
	$updated = ""
	$foundTitle = $false

	foreach ($line in ($raw -split "`r?`n")) {
		if (-not $foundTitle -and $line -match "^#\s+(.+)$") {
			$title = $Matches[1].Trim()
			$foundTitle = $true
		}
		if ($line -match "^type:\s*(.+)$") {
			$type = $Matches[1].Trim()
		}
		if ($line -match "^status:\s*(.+)$") {
			$status = $Matches[1].Trim()
		}
		if ($line -match "^updated:\s*(.+)$") {
			$updated = $Matches[1].Trim()
		}
	}

	[PSCustomObject]@{
		Path = $relative
		Title = $title
		Type = $type
		Status = $status
		Updated = $updated
		Lines = (($raw -split "`r?`n").Count)
	}
}

if ($List) {
	Get-MarkdownFiles -Path $VaultPath |
		ForEach-Object { $_.FullName }
	exit 0
}

if ($Overview) {
	Write-Output "Path`tTitle`tType`tStatus`tUpdated`tLines"
	Get-MarkdownFiles -Path $VaultPath |
		Sort-Object FullName |
		ForEach-Object {
			$note = Read-NoteOverview -File $_ -Root $VaultPath
			"{0}`t{1}`t{2}`t{3}`t{4}`t{5}" -f $note.Path, $note.Title, $note.Type, $note.Status, $note.Updated, $note.Lines
		}
	exit 0
}

if (-not $Query -or $Query.Count -eq 0) {
	throw "Pass at least one search term with -Query."
}

$normalizedQuery = @()
foreach ($item in $Query) {
	$parts = $item -split ","
	foreach ($part in $parts) {
		$trimmed = $part.Trim().Trim("'").Trim('"')
		if ($trimmed.Length -gt 0) {
			$normalizedQuery += $trimmed
		}
	}
}

if ($normalizedQuery.Count -eq 0) {
	throw "Pass at least one non-empty search term with -Query."
}

function Search-WithSelectString {
	param(
		[string]$Term,
		[string]$Path
	)

	Get-MarkdownFiles -Path $Path |
		Select-String -SimpleMatch -CaseSensitive:$false -Pattern $Term |
		ForEach-Object { "{0}:{1}:{2}" -f $_.Path, $_.LineNumber, $_.Line.Trim() }
}

$useRg = $false
$rg = $null
if ($UseRg) {
	$rg = Get-Command rg -ErrorAction SilentlyContinue
}

if ($rg) {
	try {
		& $rg.Source --version *> $null
		$useRg = $LASTEXITCODE -eq 0
	} catch {
		$useRg = $false
	}
}

foreach ($term in $normalizedQuery) {
	Write-Output "## Query: $term"
	if ($useRg) {
		try {
			& $rg.Source --line-number --ignore-case --hidden --glob "*.md" --glob "!.obsidian/**" --fixed-strings -- $term $VaultPath
		} catch {
			Search-WithSelectString -Term $term -Path $VaultPath
		}
	} else {
		Search-WithSelectString -Term $term -Path $VaultPath
	}
	Write-Output ""
}
