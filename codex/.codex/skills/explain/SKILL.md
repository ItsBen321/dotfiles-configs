---
name: explain
description: Explain project changes as a natural coworker handoff and produce a polished written companion plus human-sounding AI narration. Use when the user points to a commit, branch or revision range, pull request, patch, diff, changed paths, recent worktree changes, changes made during the current task, or other implementation work and wants to understand what changed, why it changed, how it works, or where to find it.
---

# Explain

Create an evidence-based handoff that feels like a good engineer talking a teammate through the work. Preserve precise navigation in the written companion while giving the narration only the references a person would naturally say aloud.

## Resolve the change set

1. Use the repository implied by the target or active project. Ask only when more than one repository is plausible.
2. Resolve the target before interpreting it:
   - With no explicit target, inspect staged, unstaged, and untracked worktree changes.
   - For a commit, inspect metadata, parents, the full patch, renames, file modes, and binary changes. Treat merge commits explicitly.
   - For a branch or range, record the endpoints and whether the comparison is direct or merge-base based.
   - For a pull request, patch, changed path, or conversation-scoped edit, retrieve the authoritative diff and state exactly what is in scope.
3. Read applicable repository instructions. Do not modify source files merely to explain them.
4. Inventory every changed path and hunk internally, including generated files, lockfiles, assets, deletions, modes, and submodules. Keep this inventory out of the narration unless a detail changes the listener's understanding.

## Understand the implementation

1. Read each changed hunk with enough context to understand its role. Follow only the callers, callees, data structures, configuration, and lifecycle hooks needed to reconstruct behavior.
2. Reconstruct the before-and-after behavior, control flow, state ownership, public contracts, failure paths, and interactions between files.
3. Establish intent from the user request, commit or pull-request text, tests already present in the change, documentation, names, and surrounding design. Label inferences naturally and never invent motivation.
4. Do not run tests, builds, imports, linters, formatters, smoke checks, or the application merely to explain existing changes. Treat committed or reviewed changes as already validated unless the user explicitly asks for fresh validation. Mention validation only when evidence already exists in the target, repository, or conversation and materially affects the handoff.
5. Inspect repository status only when unrelated dirty work or generated output could confuse the scope. Do not turn the handoff into a repository audit.
6. Record accurate written navigation anchors:
   - Use current working-tree line numbers for worktree changes.
   - Identify historical revisions without reading their hashes aloud.
   - Cite old locations for deleted code and both locations for useful renames.
   - Prefer the defining method, block, scene, or resource over a raw diff header.

## Write like a human coworker

Write a cohesive voice-note-style explanation, not a review checklist, forensic report, release note, or file inventory. Draft for the ear as well as the page: use complete thoughts, contractions, conversational transitions, and punctuation that creates natural breathing room.

Start with the short version: what changed and why the listener should care. Then walk through the runtime or architectural flow in the order it happens. Explain implementation details only when they help the listener understand behavior, consequences, or where to continue working.

Use these rules:

- Prefer plain language, contractions, natural transitions, and varied sentence length.
- Sound like one engineer talking one-on-one with another: warm, direct, calm, and knowledgeable.
- Do a final spoken-edit pass. Replace documentation phrases such as “this implementation introduces,” “it should be noted,” and “in summary” with direct phrasing such as “the main change is,” “the useful part is,” and “from there.” Do not add fake banter or verbal filler.
- Group related files by behavior. Do not march alphabetically through paths or announce insertion counts and hunk statistics.
- Introduce a component by its role before using its exact identifier. Say “the run coordinator” before `GAME`, for example.
- Mention exact identifiers only when the listener will need them to navigate or continue the work.
- Explain every meaningful behavior and changed artifact, but compress repetitive or mechanical edits into one natural sentence after inspecting them.
- Explain consequences and tradeoffs, not just syntax.
- Keep uncertainty, known limitations, migrations, and unfinished work when they materially affect the handoff.
- Avoid formal throat-clearing such as full authorship metadata, parent hashes, exhaustive scope counts, or “this handoff covers.”
- Prefer a focused 500 to 1,200 spoken words. Use more only when the change genuinely needs it for semantic coverage.

## Make spoken navigation natural

Never make the narration read full commit hashes, raw file-system paths, URLs, diff coordinates, or long machine identifiers. It may name a script by its basename and give a useful line number or short line range so the listener can follow along. Phrase these references as a coworker would: “in `GAME.gd`, around line 75” or “in `run-coordinator.gd`, between lines 75 and 90.” Do not speak directory chains, URI schemes, or absolute paths.

Make written navigation precise through Markdown links whose visible labels sound natural when spoken. When a script location helps the listener follow along, prefer labels such as `[the run coordinator in GAME.gd, around line 75](/absolute/repo/scripts/autoloads/GAME.gd:75)`. For non-script assets, prefer a human label such as `[the continue button scene](/absolute/repo/scenes/runs-menu/runs-menu.tscn:134)` and keep its exact location on the page. Never use a full path as the visible label.

Refer to the target conversationally as “this commit,” “the save-system change,” or a short descriptive title. If the exact revision or other machine metadata must be preserved, place it in a compact block wrapped by these markers so the renderer omits it:

```markdown
<!-- speech:skip-start -->
Technical reference: `full revision or other non-spoken metadata`
<!-- speech:skip-end -->
```

Do not put substantive explanation inside a skipped block. The Markdown remains the authoritative written companion; the audio is its intentionally humanized spoken rendition.

## Check coverage and humanity

Before rendering audio, compare the draft against the internal inventory and confirm that:

- Every changed path is explained or included in a clearly described generated or mechanical group.
- Every behavioral hunk, important failure path, and cleanup path is covered.
- Every “why” statement is supported or clearly framed as inference.
- Navigation links resolve and their visible labels sound natural without the destination.
- The opening gives a useful short version before implementation detail.
- The prose does not sound like an audit, a diff reader, or generated documentation.
- No spoken sentence contains a full hash, raw path, URL, diff coordinate, or long identifier.
- Spoken line references include a short script filename, use natural phrasing, and help the listener navigate rather than enumerate the diff.
- Reading the narration aloud would sound plausible in a coworker call.

Revise until both semantic coverage and spoken naturalness pass. Complete coverage means covering meaning, not reading the patch token by token.

## Save and render

Unless the user requests another destination, save outputs under `output/explanations/` in the active repository. Use a descriptive, collision-free stem such as `<short-topic>-handoff` and create:

- `<stem>.md`: the written companion with human-labeled navigation links.
- `<stem>.mp3`: the humanized AI narration derived from that companion.

Do not overwrite an existing output without explicit permission.

Use a high-quality local neural speech tool. Do not use Flite, eSpeak, Festival, or another concatenative or clearly robotic fallback. By default, run:

```bash
python3 <skill-directory>/scripts/render_audio.py --input <stem>.md --output <stem>.mp3
```

The bundled renderer uses the public Kokoro model locally and defaults to the `af_heart` voice. It removes non-spoken technical-reference blocks and Markdown destinations, preserves natural script-and-line cues, and stitches long transcripts by paragraph. It requires `python3`, `ffmpeg`, the `kokoro` and `soundfile` Python packages, and either system `espeak-ng` or the bundled `espeakng-loader`; it does not require an API key or paid service. If the Python packages are missing, request permission for the one-time setup, create an isolated Python 3.10–3.12 environment at `~/.local/share/codex/explain-tts`, install CPU-only PyTorch, then install `kokoro>=0.9.4`, `soundfile`, and `espeakng-loader` there. The renderer detects that environment automatically. The first render may download public model weights, after which cached rendering can run offline. Run it with `--dry-run` first to inspect the spoken character and chunk count without loading or downloading the model. Use `--force` only with explicit overwrite permission.

If neural audio rendering is unavailable, keep the finished Markdown, report the exact blocker, and ask how the user wants to proceed. Never substitute a robotic voice merely to produce an audio file.

In the final response, link both outputs, identify the explained scope in human terms, give the approximate duration, and disclose that the narration is AI-generated. Mention unrun validation only when the user asked for validation or its absence is materially important. Do not repeat the walkthrough in chat.
