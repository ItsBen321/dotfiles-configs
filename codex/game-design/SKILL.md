---
name: game-design
description: Use when Codex is asked to brainstorm, critique, research, compare, document, pitch, expand, structure, or refine game ideas, game concepts, mechanics, core loops, progression, balance, player experience, accessibility, playtesting, or non-implementation game design plans. This skill provides a portable vault-backed workflow for finding, consulting, and updating the user's game-design Obsidian vault.
---

# Game Design

Use this skill for broad game design work before implementation: concept generation, design critique, system ideation, genre analysis, player-experience goals, loops, progression, balance, accessibility, and playtest planning.

The user's durable game-design wiki lives in an Obsidian vault named `Gamedev Codex Wiki`. The local path may differ by computer.

Treat the resolved vault as editable project memory. Read it before acting, and update it when you learn durable design principles, reusable prompts, concept decisions, source notes, or user preferences.

## Vault Discovery

Resolve the vault path at the start of each task. Prefer, in order:

1. A path the user explicitly provides.
2. `GAME_DESIGN_VAULT`, `GAME_DESIGN_VAULT_PATH`, or `CODEX_GAME_DESIGN_VAULT`.
3. A local config file at `~/.codex/game-design-vault.txt` or `~/.codex/game-design-vault.path` containing the vault path.
4. Obsidian's local vault registry (`obsidian.json`) on Windows, macOS, or Linux.
5. A common-folder search for an Obsidian vault folder named `Gamedev Codex Wiki`.

Use the bundled helper to resolve and print the current path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -PrintPath
```

If discovery fails, ask the user for the vault path and suggest saving it in `~/.codex/game-design-vault.txt` on that computer.

## Vault Navigation Tools

In Codex Desktop on Windows, direct `rg` vault search may be blocked with `Access is denied`. Start with the bundled PowerShell helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Overview
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Query "core loop","progression"
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -List
```

For direct navigation, use PowerShell-native commands:

```powershell
$VaultPath = powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -PrintPath
Get-ChildItem -LiteralPath $VaultPath -Recurse -File -Filter "*.md" |
	Where-Object { $_.FullName -notmatch "\\.obsidian\\" } |
	Select-Object -ExpandProperty FullName
```

Only use `rg` for vault search if the user explicitly requests it or you have already verified that it runs without errors in the current environment.

## Core Workflow

1. Identify the design task.
   - Separate concept/design work from implementation work.
   - Name the requested artifact: brainstorm, critique, concept pitch, design doc, mechanic set, progression plan, content plan, playtest plan, or research note.
   - If the task implies a game project, search for an existing project or concept note before creating new structure.

2. Consult the editable design vault.
   - Start with `INDEX.md`.
   - For broad or unfamiliar tasks, run the helper with `-Overview` to see note titles, types, statuses, update dates, and line counts before opening files.
   - Do a lightweight index-routing pass: identify likely buckets such as foundations, workflows, templates, concept notes, source notes, preferences, or project-specific material.
   - Search exact task terms, related genre terms, reference games, mechanics, desired feelings, loop/progression terms, and player audience terms.
   - Read the smallest relevant notes first. Follow Obsidian links only when directly relevant.

3. Research when needed.
   - Use online research when the user asks for it, when the design topic benefits from external examples, or when a claim may be outdated.
   - Prefer primary, durable, or well-established sources: original papers, designer essays, official accessibility guidance, GDC/GameDeveloper talks/articles, and reputable design books/sites.
   - Store reusable research as concise source notes with links and a "Design Use" section.

4. Design from player experience outward.
   - Start with the intended player experience, fantasy, motivation, or emotional target.
   - Translate that into dynamics, then mechanics, content, constraints, feedback, and progression.
   - Keep implementation/engine choices out of the answer unless the user asks for them or they affect design feasibility.

5. Produce the requested artifact.
   - For brainstorms: explore divergent options, then cluster and rank the strongest directions.
   - For critiques: lead with design risks and mismatches between experience goals, mechanics, and audience.
   - For concept docs: use the vault templates and keep the core loop, hook, design space, progression, and validation plan explicit.
   - For playtest plans: define hypothesis, scope, target players, tasks, observations, questions, success signals, and next iteration.

6. Update the editable vault.
   - Add or edit notes when a new durable rule, source, concept, project decision, reusable prompt, design pattern, or user preference appears.
   - Keep notes concise, linked, and evidence-backed.
   - Mark speculation as hypothesis or draft.
   - When creating a top-level topic, update `INDEX.md`.
   - For substantial vault edits or uncertain placement, load `references/vault-update-rules.md`.

## Vault Rules

- Prefer active notes over draft or deprecated notes.
- If notes conflict, follow the most specific active concept/project note, then user instructions, then general design principles. Mention unresolved conflicts.
- Preserve user-authored context. Update notes by refining or appending rather than erasing useful history.
- Do not store secrets, private one-off logs, or unsupported guesses as durable truth.
- Do not overwrite the user's creative intent with generic best practices. Use frameworks to sharpen the idea, not flatten it.

Use frontmatter in new notes:

```yaml
---
type: index | principle | framework | workflow | concept | template | source | preference | decision | audit | example
status: active | draft | deprecated
applies_to: [game-design]
updated: YYYY-MM-DD
sources: []
---
```

## Reference Files

- `references/vault-workflow.md`: How to search, read, and update the editable vault.
- `references/vault-update-rules.md`: Detailed rules for what to store, where to put it, conflicts, quality bar, and maintenance checks.
- `references/concept-development.md`: Practical workflow for brainstorming, narrowing, critiquing, and documenting game concepts.
- `references/design-lenses.md`: Compact guide to MDA, design tools, loops, motivation, accessibility, playtesting, and the user's recurring design preferences.
- `references/artifact-templates.md`: Output shapes for concept briefs, critique notes, research notes, and playtest plans.

Load only the reference file needed for the current task.
