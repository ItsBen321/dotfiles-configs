---
name: godot-gdscript
description: Use whenever Codex is asked to create, edit, review, debug, test, document, architect, refactor, or explain anything related to Godot Engine, GDScript, Godot scenes/resources, Godot addons/plugins, Godot CLI/testing, or the user's Godot projects. This skill provides a portable vault-backed workflow for finding, consulting, and updating the user's Godot Obsidian vault and applying the user's Godot architecture, style, and validation guidance.
---

# Godot GDScript

Use this skill as the entry point for all Godot and GDScript work. The user's durable project knowledge lives in an Obsidian vault named `Godot Codex Wiki`. The local path may differ by computer.

Treat the resolved vault as editable project memory. Read it before acting, and update it when you learn durable Godot, GDScript, project architecture, workflow, or user preference information.

## Vault Discovery

Prefer the sibling `vault-retrieval` skill's helper for retrieval and discovery. It adds per-desktop config and automatic catalogue refresh to the existing discovery options. If the shared skill is missing, disabled, or Jev fails, use the original discovery and search workflow below immediately; do not block Godot work on Jev setup.

For that fallback, `vault-retrieval/scripts/retrieve.py path --profile godot` still resolves the configured path without Jev, even while disabled; pass it to the existing helper's `-VaultPath` or use native file reads. If the shared helper is unavailable, resolve the vault path at the start of each task. Prefer, in order:

1. A path the user explicitly provides.
2. `GODOT_CODEX_VAULT`, `GODOT_CODEX_VAULT_PATH`, or `CODEX_GODOT_VAULT`.
3. A local config file at `~/.codex/godot-codex-vault.txt` or `~/.codex/godot-codex-vault.path` containing the vault path.
4. Obsidian's local vault registry (`obsidian.json`) on Windows, macOS, or Linux.
5. A common-folder search for an Obsidian vault folder named `Godot Codex Wiki`.

Use the bundled helper to resolve and print the current path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -PrintPath
```

If discovery fails, ask the user for the vault path and suggest saving it in `~/.codex/godot-codex-vault.txt` on that computer.

## Vault Navigation Tools

Preferred retrieval (load the sibling `vault-retrieval/SKILL.md` when first using it):

```sh
python3 "<skills-directory>/vault-retrieval/scripts/retrieve.py" retrieve --profile godot --task "Concrete Godot task and relevant subsystems"
```

Use `python` on Windows. Pass `--project "Existing Project Note Title"` when known, `--vault` for a user-provided path, and `--include-note "Workflows/Godot MCP Tool Routing.md"` whenever `mcp__godot__` is available. Read the returned guidance directly with a tool output limit around 12,000 tokens. The helper returns the index and mandatory editing, typing, and validation notes in full, followed by original excerpts. Fetch specific complete notes with its `read` command when passages are incomplete.

Disable with `retrieve.py configure --disable`, re-enable with `configure --enable`, or temporarily disable with `VAULT_RETRIEVAL_ENABLED=0`. A disabled helper (exit 3) or any failed Jev call means use the existing workflow below, without repeated API attempts.

For fallback navigation in Codex Desktop on Windows, `rg` may be blocked with `Access is denied`. Do not probe, retry, or announce a fallback from `rg` just to navigate the Godot vault. Start with the bundled PowerShell helper, which uses PowerShell-native search by default:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Overview
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Query "term one","term two"
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -List
```

For direct vault navigation, use PowerShell-native commands:

```powershell
$VaultPath = powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -PrintPath
Get-ChildItem -LiteralPath $VaultPath -Recurse -File -Filter "*.md" |
	Where-Object { $_.FullName -notmatch "\\.obsidian\\" } |
	Select-Object -ExpandProperty FullName

Get-ChildItem -LiteralPath $VaultPath -Recurse -File -Filter "*.md" |
	Where-Object { $_.FullName -notmatch "\\.obsidian\\" } |
	Select-String -SimpleMatch -CaseSensitive:$false -Pattern "search term" |
	ForEach-Object { "{0}:{1}:{2}" -f $_.Path, $_.LineNumber, $_.Line.Trim() }
```

Only use `rg` for vault search if the user explicitly requests it or you have already verified that it runs without errors in the current environment.

## Core Workflow

1. Find the project root.
   - Prefer the nearest directory containing `project.godot`.
   - Read any applicable `AGENTS.md` or repository guidance before editing.
   - Use `scripts/project_inventory.ps1` when a quick project map would help.

2. Consult the vault.
   - Prefer one call to the shared retrieval helper above. Use its full index as the routing map and inspect the returned passages for coverage; fetch a specific original when needed.
   - If that helper is missing, disabled, or fails, start with `INDEX.md`, identify relevant categories, and search with exact task terms, class/scene names, and related Godot concepts using the existing helpers. For broad tasks, use `scripts/search_vault.ps1 -Overview` before opening files.
   - Read the smallest relevant notes first. Follow Obsidian links only when they are directly relevant.
   - If a Godot project root was found, check whether that project exists under `Project Notes` or is linked from `Project Notes/Project Notes Index.md`. Search by folder name, project name, main scene, and any known game title. Pass the matching note title as `--project`; an exact matching root is included in full. Read the active project note before editing when one exists.
   - Treat vault use as iterative. Revisit the vault while implementing whenever the work touches a new subsystem, architecture choice, scene/resource format, node reference pattern, input map, physics/collision setup, test workflow, or validation command.

3. Inspect the Godot project.
   - Read the relevant `.gd`, `.tscn`, `.tres`, `.res`, `.gdshader`, `project.godot`, addon, and test files.
   - Check autoloads, signals, scene ownership, exported properties, resources, and any test framework before changing behavior.
   - Before adding or changing node references, inspect the owning scene and revisit the relevant vault note.

4. Make scoped changes.
   - Follow the project's existing architecture and the vault's active rules.
   - Prefer composition, small independent scripts, typed GDScript, readable names, and clear scene/resource boundaries.
   - Avoid broad rewrites, speculative abstractions, and unrelated formatting churn.
   - When adding a new gameplay feature, actor controller, AI behavior, turn/action flow, reusable component, or structural pattern, read `references/game-architecture.md` before choosing the implementation shape.
   - Do not rely only on the initial vault read. Before writing code that chooses between engine/editor features and script-only substitutes, search the vault again with the concrete Godot terms now visible in the implementation.

5. Verify.
   - Use Godot CLI, tests, linter/formatter, or project-specific commands when available.
   - Read `references/validation.md` when choosing commands.
   - If verification cannot run, explain exactly what was not run and why.

6. Update the vault.
   - Add or edit notes when the user gives a new rule, a project architecture fact is discovered, a recurring pitfall is found, or a validation workflow changes.
   - Keep notes concise, linked, and evidence-backed.
   - Do not store secrets, one-off logs, or transient speculation as durable truth.
   - When creating a top-level topic, update `INDEX.md`.

## Vault Rules

- Prefer active notes over deprecated notes.
- If notes conflict, follow the most specific active project note, then repository guidance, then general Godot notes. Mention unresolved conflicts.
- Preserve user-authored context. Update notes by refining or appending rather than erasing useful history.
- Use frontmatter in new notes:

```yaml
---
type: rule | pattern | workflow | architecture | pitfall | reference | decision | index
status: active | draft | deprecated
applies_to: [godot, gdscript]
updated: YYYY-MM-DD
---
```

## Reference Files

- `references/vault-workflow.md`: How to search, read, and update the Obsidian vault.
- `references/gdscript-style.md`: Baseline GDScript style and architecture preferences.
- `references/game-architecture.md`: Pattern-selection guidance for state machines, AI, commands, queues, components, resources, pools, and other recurring game feature structures.
- `references/validation.md`: Godot CLI, formatter, linter, and test guidance.

Load only the reference file needed for the current task.
