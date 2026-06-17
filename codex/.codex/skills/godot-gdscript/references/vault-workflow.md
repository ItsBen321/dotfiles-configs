# Vault Workflow

The editable vault is the user's local Obsidian vault named `Godot Codex Wiki`. Resolve the local path before reading or editing notes.

Use this order:

1. User-provided path.
2. `GODOT_CODEX_VAULT`, `GODOT_CODEX_VAULT_PATH`, or `CODEX_GODOT_VAULT`.
3. `~/.codex/godot-codex-vault.txt` or `~/.codex/godot-codex-vault.path`.
4. Obsidian's local vault registry.
5. Common-folder search for `Godot Codex Wiki`.

## Search Order

1. Read `INDEX.md`.
2. Do a lightweight index-routing pass. Scan the `INDEX.md` map and list the likely buckets for the task: project note, workflow, GDScript, architecture, Godot system, validation, or tooling.
3. If a Godot project root is known, check project-specific notes first. Search `Project Notes`, `Project Notes/Project Notes Index.md`, the project folder name, the game title, the main scene, and notable autoload names.
4. Search exact identifiers from the task: file names, scene names, class names, node names, autoload names, and feature names.
5. Search related concepts from the selected index buckets, not only terms named by the user: signals, resources, state machines, UI, save data, tests, input, physics, animation, or addon names.
6. Follow only directly relevant `[[links]]`.

## Index Routing Pass

Use the index as a menu, not as content to memorize. The goal is to choose a small set of notes that could govern the implementation.

- Pick likely notes before searching deeply.
- Include project-specific notes when they exist.
- Include workflow notes when the task touches editing, validation, debugging, formatting, testing, or collaboration. For script, scene, resource, addon, or node-reference edits, route through `Workflows/Manual Editing Rules`.
- Include architecture notes when the task changes ownership, scenes, data definitions, dependencies, or cross-system communication.
- Include Godot system notes when the task touches engine behavior, editor-owned configuration, scene/resource files, input, physics, UI, rendering, animation, navigation, networking, export, threading, async, or lifecycle behavior.
- Do not load every candidate note. Search inside the selected area and read the smallest relevant notes first.

## Revisit During Implementation

Do not treat the first vault read as complete. Re-query the vault whenever implementation reveals a new concrete term or decision point.

Revisit especially before:

- Adding node references or editing scene paths. Search the concrete node, scene, ownership, and reference-pattern terms visible in the task.
- Choosing between script-built setup and editor/project-owned configuration. Search the concrete feature, such as `Input Map`, `Project Settings`, `Timer`, `AnimationPlayer`, `CollisionShape`, or `PackedScene`.
- Creating data structures that may belong in resources, custom classes, scenes, CSV/JSON, or files.
- Touching physics, input, UI focus, pause/timers/tweens, threading, async/await, scene inheritance, autoloads, or signals.
- Selecting validation commands or test workflows.

Use the bundled PowerShell helper first. It avoids direct `rg` calls by default, which matters in Codex Desktop environments where `rg` can be blocked with `Access is denied`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -PrintPath
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Overview
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Query "spin","roulette"
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -List
```

Use `-Overview` when the task is broad, the best route is unclear, or the vault has grown since the last run. It returns note path, title, type, status, update date, and line count without loading every file.

For one-off manual searches, use PowerShell-native commands:

```powershell
$VaultPath = powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -PrintPath
Get-ChildItem -LiteralPath $VaultPath -Recurse -File -Filter "*.md" |
	Where-Object { $_.FullName -notmatch "\\.obsidian\\" } |
	Select-String -SimpleMatch -CaseSensitive:$false -Pattern "spin" |
	ForEach-Object { "{0}:{1}:{2}" -f $_.Path, $_.LineNumber, $_.Line.Trim() }
```

Only use direct `rg` vault search if the user asks for it or it has already been verified in the current environment.

## Update Rules

Update the vault when information is durable and likely to help future Godot work:

- User style preferences.
- Architecture decisions.
- Project structure and ownership.
- Known bugs, pitfalls, and fixes.
- Repeatable validation commands.
- Godot/GDScript research that changes future implementation choices.

Avoid storing:

- Secrets or credentials.
- Raw temporary logs.
- Unverified guesses presented as facts.
- Large pasted documentation when a short summary and source link is enough.

## Note Shape

Use short notes with one clear purpose. Put the most actionable rule near the top.

```markdown
---
type: pattern
status: active
applies_to: [godot, gdscript]
updated: 2026-04-26
---

# Topic Name

## Use This When

## Guidance

## Evidence

## Links
```
