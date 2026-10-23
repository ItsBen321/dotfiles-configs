# Desktop setup and maintenance

The shared skill lives in the dotfiles repo at `codex/.codex/skills/vault-retrieval`. Install the repo's `codex` package using the existing dotfiles setup (GNU Stow where available), or link/copy this folder into your Codex skills directory. Install `godot-gdscript` and `game-design` alongside it. No machine-specific paths belong in these skill files.

The helper needs Python 3.9 or newer and only the standard library. Use `python3` on Linux/macOS and `python` on Windows. Commands below assume the installed skill location; adjust it if `CODEX_HOME` is customized.

## Configure once per desktop

```sh
python3 ~/.codex/skills/vault-retrieval/scripts/retrieve.py configure --profile godot --vault "/path/to/Godot Codex Wiki"
python3 ~/.codex/skills/vault-retrieval/scripts/retrieve.py configure --profile game-design --vault "/path/to/Gamedev Codex Wiki"
```

Windows example:

```powershell
python "$HOME/.codex/skills/vault-retrieval/scripts/retrieve.py" configure --profile godot --vault "D:/Obsidian/Godot Codex Wiki"
```

Explicit `--vault` takes priority, followed by the domain skill's vault environment variables, this helper's per-desktop config, existing `~/.codex/*-vault.txt`/`.path` files, Obsidian's registry, and common folders. A vault must have `INDEX.md`. Symlinked notes and hidden directories are excluded.

For Jev, use the installed CLI and run `jev setup` locally to store the credential in its keyring. Authenticate separately on each desktop. This helper never stores the key. A CLI launcher with extra arguments can be configured with `configure --jev-command-json '["python3", "/path/to/jev.py"]'`. Use an absolute launcher path where possible. This setting is a JSON argument array, not a shell command; it must contain no secrets.

Without a CLI, the helper can call the documented TypeSafe HTTP API directly using `TYPESAFE_API_KEY` supplied by your local secret manager or process environment. This provides a standard-library alternative on desktops without the CLI. Only note descriptors (titles, author-written descriptions, use cases, search terms, headings) and the task are sent for ranking; the final passages are copied locally from originals.

## Easy disable and fallback

```sh
python3 ~/.codex/skills/vault-retrieval/scripts/retrieve.py configure --disable
python3 ~/.codex/skills/vault-retrieval/scripts/retrieve.py configure --enable
```

Disabling persists for this desktop. `VAULT_RETRIEVAL_ENABLED=0` disables it temporarily (`1` overrides config to enable). Disabled retrieval returns exit code 3 before vault reads or network calls. A failed Jev request returns exit code 1. Both domain skills then use their existing index/search/read workflow. `path --profile godot` (or `game-design`) still prints the configured path without Jev; pass it to the existing search helper's `-VaultPath` or use native file reads. There are no automatic API retries after an authentication, quota, or network failure. `retrieve --offline` offers a separate local keyword ranking option without API usage, while enabled.

## Local files

| System | Config | Cache |
| --- | --- | --- |
| Linux | `$XDG_CONFIG_HOME/vault-retrieval/config.json` or `~/.config/vault-retrieval/config.json` | `$XDG_CACHE_HOME/vault-retrieval` or `~/.cache/vault-retrieval` |
| macOS | `~/Library/Application Support/vault-retrieval/config.json` | `~/Library/Caches/vault-retrieval` |
| Windows | `%APPDATA%/vault-retrieval/config.json` | `%LOCALAPPDATA%/vault-retrieval` |

Global `--config PATH` and `--cache-dir PATH` precede the subcommand. Config accepts `version`, `profiles`, `enabled`, `jev_command`, and `model`; no credential fields. Example:

```json
{
  "version": 1,
  "enabled": true,
  "profiles": {
    "godot": {
      "vault": "/local/vault/path",
      "required": ["Workflows/My Required Rule.md"]
    }
  }
}
```

Deleting the cache is safe. Each retrieval hashes visible Markdown notes, re-extracts changed metadata, and rebuilds category membership. A changed index refreshes author-written descriptions. It checks for changes again after Jev responds and retries selection once if the vault changed, recording both attempts' usage. Continuous changes stop retrieval rather than mix versions. Concurrent desktops maintain separate caches.

Categories derive from folders, with large folders split by their topic tags. Jev selects relevant branches, then scores candidate note descriptions in bounded batches. Required notes bypass scoring. Low category confidence broadens the search; selection quality still needs judgment from the consuming skill.

## Vault-controlled routing

New notes need no skill update. Use ordinary `applies_to`/`tags`, descriptive headings, and a `Use This When` section. Optional frontmatter:

```yaml
retrieval_required: true
retrieval_category: Godot/Physics
```

For shared routing rules across desktops, optionally add `vault-retrieval.json` at the vault root:

```json
{
  "required": ["Workflows/Team Rules.md"],
  "category_descriptions": {
    "Godot/physics": "Collision, body motion, and safe physics state changes"
  }
}
```

Profile defaults always include the index; Godot also includes manual editing, style/typing, and CLI validation. Game design includes user design preferences. Deprecated required notes cause an explicit failure. Use `index --profile godot` to inspect current category IDs when changing routing; avoid sending this diagnostic catalogue into normal task context.

Named project/concept notes are considered only with `--project`; an exact matching root note is mandatory. `--include-note` can pin an exceptional note explicitly.

## Output and usage

Default stdout starts with a 28,000-character budget, with full required notes and original excerpts of up to about 1,800 characters per selected note. The default budget automatically grows to fit all required originals plus bounded optional excerpts. At most eight optional notes are selected by default; adjust `--max-notes` for a specific task. Explicit `--max-chars` is a hard limit: required content that cannot fit fails before paid API calls and is never silently truncated. Stderr reports `output_chars` and `max_chars`; if an execution tool truncates the returned output, read required notes in chunks using `read --note` and its `next_line` continuation. Saved `full-notes.md` contains all selected originals, including those omitted from stdout by its budget.

Stderr points to a local `result.json` containing selected/returned/omitted IDs, refresh information, end-to-end helper latency, API calls, and actual Jev input/output tokens. These metrics exclude Codex processing time and usage. The model defaults to `jev-1.13.0`; verify [current TypeSafe models](https://docs.typesafe.ai/models) when changing it. API contract: [HTTP API](https://docs.typesafe.ai/api).

Run offline behavioral checks with `python3 -m unittest discover -s "<skill>/tests" -v`. Linux runtime and live CLI integration are tested here; Windows/macOS path handling is tested without running those desktops.
