# Vault Workflow

The editable vault is the user's local Obsidian vault named `Gamedev Codex Wiki`. Resolve the local path before reading or editing notes.

Use this order:

1. User-provided path.
2. `GAME_DESIGN_VAULT`, `GAME_DESIGN_VAULT_PATH`, or `CODEX_GAME_DESIGN_VAULT`.
3. `~/.codex/game-design-vault.txt` or `~/.codex/game-design-vault.path`.
4. Obsidian's local vault registry.
5. Common-folder search for `Gamedev Codex Wiki`.

## Search Order

1. Read `INDEX.md` in the editable vault.
2. Do an index-routing pass. Choose likely buckets: foundations, workflows, templates, concepts, source notes, preferences, or project notes.
3. Search exact task terms, reference games, genre names, mechanics, player feelings, loop/progression language, and design risks.
4. Follow only directly relevant `[[links]]`.

Use the bundled helper first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -PrintPath
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Overview
powershell -NoProfile -ExecutionPolicy Bypass -File "<path-to-this-skill>\scripts\search_vault.ps1" -Query "core loop","player motivation"
```

Use `-Overview` when the request is broad or the best route is unclear. It is faster than opening every note because it returns the note path, title, type, status, update date, and line count.

## Update Rules

Update the editable vault when information is durable and likely to help future design work:

- User design preferences.
- Concept decisions or discarded alternatives.
- Reusable design patterns, lenses, and prompts.
- Research summaries with links.
- Playtest findings and follow-up hypotheses.

Avoid storing:

- Secrets or private credentials.
- Raw temporary logs.
- Unsupported guesses presented as facts.
- Large pasted documentation when a short summary and link is enough.

## Note Shape

Use short notes with one clear purpose. Put the actionable rule or design use near the top.

```markdown
---
type: principle
status: active
applies_to: [game-design]
updated: 2026-05-20
sources: []
---

# Topic Name

## Use This When

## Guidance

## Evidence

## Links
```

## Conflict Handling

If notes conflict, use this priority order:

1. The user's latest direct instruction.
2. Active concept or project notes.
3. Active user preference notes.
4. General foundations and source notes.
5. Draft notes and speculation.

Mention unresolved conflicts briefly instead of silently choosing a weak assumption.
