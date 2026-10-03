---
name: vault-retrieval
description: Retrieve relevant original guidance from the Godot or game-design Obsidian vault for a vault-backed skill, using Jev routing and a local catalogue that refreshes automatically.
---

# Vault Retrieval

Use this as a retrieval layer for `godot-gdscript` (`--profile godot`) or `game-design` (`--profile game-design`). The domain skill continues to own implementation, design, validation, and vault updates.

Run the helper once with the concrete task, without reading its source or dumping the catalogue:

```sh
python3 "<path-to-this-skill>/scripts/retrieve.py" retrieve --profile godot --task "Describe the requested change and important subsystems"
```

Use `python` on Windows. Pass `--vault` for a user-provided path, and `--project "Existing Note Title"` for an existing project or concept. Omit `--project` for a new game; unrelated named projects are excluded. For a long prompt, use `--task-file` instead of shell interpolation. Add an explicitly needed source with `--include-note "Folder/Note.md"`.

The helper includes `INDEX.md` and the profile's mandatory guidance in full, then bounded passages copied from the selected originals. Set the execution tool's output limit high enough for the default 28,000 characters (about 12,000 tokens). Read this output directly; do not print the saved full bundle by default. Excerpts are partial evidence, and the index remains a routing map. If relevant guidance is missing or incomplete, fetch the specific note:

```sh
python3 "<path-to-this-skill>/scripts/retrieve.py" read --profile godot --note "Godot/Relevant Note.md" --start-line 1
```

The read command reports the next line on stderr. Request that line to continue. Re-run retrieval when the task reveals a new subsystem. Each retrieval detects note edits, additions, renames, deletions, and routing changes; vault maintenance does not require rewriting this skill.

If retrieval exits with code 3 (`disabled`), use the domain skill's original discovery, index, and search workflow immediately. If Jev fails, is unavailable, or has exhausted quota, use that same workflow without repeated retries or blocking the task on credential setup. `path --profile godot` (or `game-design`) prints the configured vault path even while disabled; pass it to the domain search helper's `-VaultPath`, or use it for native file reads. `--offline` is an optional scripted local search, when explicitly useful; it does not replace the default fallback.

Disable or re-enable this layer on the current desktop:

```sh
python3 "<path-to-this-skill>/scripts/retrieve.py" configure --disable
python3 "<path-to-this-skill>/scripts/retrieve.py" configure --enable
```

`VAULT_RETRIEVAL_ENABLED=0` temporarily disables it and takes precedence over local config. Read [references/setup.md](references/setup.md) only for desktop setup, custom required notes/categories, or troubleshooting. Credentials, absolute vault paths, cached catalogues, and request logs stay outside the dotfiles repo.
