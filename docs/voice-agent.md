# Voice-controlled desktop agent

The existing local dictation pipeline can hand a transcript to a background
Codex CLI process. The agent prefers terminal commands, installed application
interfaces and launchers, and uses desktop tools when needed.

| Shortcut | Action |
| --- | --- |
| Mod+D | Start/finish ordinary dictation into the focused application |
| Mod+Shift+D | Start/finish dictating a task for Codex |
| Mod+Ctrl+Shift+D | Cancel the running agent and background learning |
| Mod+Alt+Shift+D | Confirm the exact pending consequential action within two minutes |

The shortcut that **starts** a recording chooses its destination. A task is
never typed into the focused application. One desktop task runs at a time;
finish or cancel it before starting another recording. Cancellation stops the
runner's process group; it cannot undo actions already completed or stop an
application that has detached into its own session.

## Installation

Requires the existing PipeWire/Whisper dictation setup, Python 3.11+, the overlay's
GTK3/PyGObject/Cairo dependencies, and a logged-in Codex CLI. Tested against
Codex CLI 0.164.0, including `--ignore-user-config` and `--approve-for-me`.
Model credentials stay in the normal local Codex installation. No separate API
key is required when the CLI is already logged in with ChatGPT.

The `hypr` Stow package contains the executable and its instruction/schema files.
Existing absolute symlinks can cause Stow conflicts; do not overwrite unrelated
files to resolve them. To install only the new runner from the repository root:

```bash
ln -s "$PWD/hypr/.local/bin/voice-agent" "$HOME/.local/bin/voice-agent"
ln -s "$PWD/hypr/.local/share/voice-agent" "$HOME/.local/share/voice-agent"
```

The recorder also locates the runner beside its resolved script path, so the
shortcut works with the repository's existing voice-dictation symlink. The
Hyprland config adds the bindings; reload the config if they are not picked up
automatically. Each invocation runs without the shared Codex daemon so the
runner can manage its own process group. It does not start a persistent model process.

```bash
~/.local/bin/voice-agent doctor
printf '%s' 'Find where Firefox is installed; do not launch it.' | ~/.local/bin/voice-agent run
~/.local/bin/voice-agent cancel
```

Results appear in the overlay and a desktop notification. The overlay shows the
transcribed request while working. `last-result.json` in the runtime directory
contains the full result, including any confirmation proposal.

## Speed and memory

Each request starts with compact instructions and a small selection of relevant
cached facts. The default reasoning effort is `medium`; only the model name is
inherited from the normal Codex config. The coding config's MCP servers, hooks,
apps and reasoning effort are not inherited. Foreground runs use automatic
approval review with the workspace-write sandbox. There is no unsandboxed default
and no fixed-command replay that bypasses the agent's judgment.

Memory lives in `$XDG_STATE_HOME/voice-agent/memory.json`, normally
`~/.local/state/voice-agent/memory.json`. It is private to the current machine and
user, with a mode-700 directory and mode-600 atomic file writes. It is never
stored in the public checkout. Entries contain a stable key, a concise fact,
the command that supplied evidence, a kind, and an observation timestamp.
Positive facts require a successful command with observable output. Failed
approaches retain the failed command, its error and task context. A failed
compound shell command does not imply every subcommand failed; failure entries
guide diagnosis rather than permanently banning a program. Legacy facts without
this provenance are marked as weaker hints.

For example, after a verified Steam task, it can remember Deadlock's app ID and
the working launch syntax. It should not remember a transient PID, window ID,
one-off search, or the contents of a personal document.

The task result is displayed **before** a separate background learning pass is
started. That pass receives bounded command evidence from the completed task
and proposes at most five reusable facts. Only entries tied to a successful
command are accepted; deciding whether evidence supports a fact still depends
on the model. A zero exit code alone is not sufficient proof in its instructions.
Known commands skip another model call. Observed failures are saved before the
optional learning model starts, so interrupting that model does not lose them.
Failed tasks can invalidate facts and preserve negative evidence, but cannot
teach positive facts. A bare zero exit from `app &` is not enough to remember a
working launch method. Expired entries are ignored, and fresh requests preempt learning.

Learning uses another Codex invocation and therefore some additional account
usage. Its shell, browser and computer tools are disabled, it has a read-only
sandbox, and its instructions prohibit operating the PC. It is optional and has
a separate timeout. If learning fails or is interrupted, the task result is
unaffected. Interrupting it may mean that task's discovery is not remembered.

The cache holds at most 80 entries by default, expires facts after 30 days, and
supplies at most 10 relevant entries / 5000 serialized characters per request.
Retrieval uses local keyword overlap; it does not require an embeddings service.
The task agent must inspect current state and recover if a fact proves stale.
Cached text is treated as untrusted data, never as new instructions or permission.

```bash
~/.local/bin/voice-agent memory show
~/.local/bin/voice-agent memory clear
```

Clearing memory prevents an older learning pass from restoring the cleared data.

## Configuration and desktop support

Copy `.local/share/voice-agent/config.example.toml` from the `hypr` package to
`~/.config/voice-agent/config.toml` for private overrides. The example documents
model, reasoning, timeout, memory size, and expiration settings. Set
`memory_enabled = false` to disable learning and retrieval. Override `model` if
the model selected by the normal CLI config is unsuitable; reasoning support
depends on that model. No measured latency improvement is claimed.

Fast mode is separate from reasoning effort. `fast_mode = false` is the default;
set it to `true` to request the model's `fast` service tier for foreground tasks
when supported. Fast can consume more account usage. Background learning keeps
the normal tier. The runner does not inherit the normal Codex config's tier.
`skills_context_tokens = 512` limits unrelated skill-catalog context for desktop
tasks; learning uses the smallest supported positive catalog budget.

For persistent GUI programs, the agent uses:

```bash
~/.local/bin/voice-agent launch -- mpv /path/to/video.mp4
```

This creates a transient systemd user service, forwards the desktop connection
variables, and checks that its process is running. It avoids losing a plain
background child when a short-lived command tool exits. It does not itself prove
playback or a visible window, and still needs desktop access through the normal
automatic approval mechanism when invoked inside the sandbox.

`firefox`, `steam`, `hyprctl`, `grim` and `wtype` provide useful launch, inspection,
screenshot and keyboard operations when installed. The agent can run those
through terminal tools, requesting automatically reviewed desktop access when
needed. GUI interaction depends on the compositor, focused window and tool
permissions. `ydotool` mouse control additionally needs its daemon and configured
`/dev/uinput` access; this implementation does not install or grant that access.
General Firefox page inspection/navigation would need a browser integration;
opening a search URL already works through Firefox's launcher.

Consequential actions are handled by a pending proposal and the confirmation
shortcut. Confirmation is single-use, expires after two minutes, and covers only
the displayed proposal. Starting another request or cancelling discards it.
The agent instructions govern when it asks: this is a behavioral safeguard,
not a complete security boundary. Automatic review and OS permissions remain
independent enforcement layers. A denied action is reported, not retried with
weaker settings.

## Privacy, troubleshooting and validation

Audio transcription stays local. The transcript, task evidence, relevant cached
facts and any supplied screenshots go to the Codex model service. Do not commit
recordings, transcripts, authentication files, private overrides or learned data.
Instructions prohibit reading credentials and storing secrets; pattern checks on
memory provide an additional filter, not a guarantee against arbitrary secrets.

Runtime files are under `$XDG_RUNTIME_DIR/voice-agent-UID` (or `/tmp` if unset),
with private permissions. `task.stderr.log`, `task.events.jsonl`,
`memory.stderr.log`, `memory.events.jsonl`, and `learning.log` help diagnose
failures. Logs from the last invocation are overwritten. Pending learning jobs
are removed when read; an abruptly killed process can leave a private job file.
The recorder's `agent-launch.log` is in its existing runtime directory.

`task.timing.json` and `memory.timing.json` record elapsed event times, command
event spans, model usage and requested tier. Spans use CLI event receipt time,
so buffering can affect them; they are not exact subprocess execution durations.
Events also contain
`voice_agent_elapsed_seconds`. The recorder's `timing.jsonl` records recording
stop, transcription and agent-dispatch timestamps. These separate microphone,
transcription, CLI/model/tool and post-task learning delays on future requests.

An investigated first playback request spent approximately 1.4 seconds in local
transcription and 59.5 seconds in the agent. It made eight command attempts,
including failed window inspection and repeated background launches and IPC
checks. The 6.2-second memory pass ran afterward and did not delay the result.
The old log had no per-event times, so it cannot establish the exact split
between provider, approval and command time. The persistent launcher and shorter
task instructions address the observed retries; timing logs measure the result.

No real desktop action is needed for the automated tests:

```bash
python3 -m unittest discover -s tests -v
bash -n hypr/.local/bin/voice-dictation
luac -p hypr/.config/hypr/hyprland.lua
```

The tests use a fake CLI to exercise event parsing, task locking, result-before-
learning ordering, interruption, process-group termination, cache relevance,
expiration, evidence validation, invalidation, private writes and confirmation.
They do not verify microphone transcription or real GUI automation.

Codex interfaces: [non-interactive runs](https://learn.chatgpt.com/docs/non-interactive-mode)
and [configuration reference](https://developers.openai.com/codex/config-reference).
