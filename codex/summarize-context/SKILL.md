---
name: summarize-context
description: Produce a structured, human-readable inventory of what the agent currently has in context. Use when the user asks to summarize context, inspect context, show what the chat context contains, describe loaded instructions/skills/tool outputs/files, or explain what the agent can and cannot currently see.
---

# Summarize Context

## Goal

Give the user a practical inventory of the agent's current usable context. Be explicit about what is visible, what is inferred, and what cannot be inspected exactly.

This skill is for context transparency, debugging, handoff, and understanding why the agent is behaving a certain way.

## Workflow

1. Build the inventory from current accessible context only.
   - Include instructions, conversation, loaded skills, tool outputs, files read, files edited, environment facts, and known constraints.
   - Do not claim to expose hidden system state, encrypted reasoning, or the exact byte-for-byte model input.
   - If exact details are unavailable, say so plainly.

2. Separate the report into these sections:
   - **System/Developer Instructions**
   - **User Conversation**
   - **Loaded Skills**
   - **Tool Outputs**
   - **Files Read Or Edited**
   - **Environment And Settings**
   - **Inferred Or Unknown Parts**

3. Keep the report useful rather than exhaustive noise.
   - Summarize long instruction blocks by intent and constraints.
   - List concrete paths, commands, tools, and important outputs when known.
   - Mark stale metrics as stale if additional turns have happened since they were collected.
   - Do not dump raw logs unless the user explicitly asks.

4. Use careful wording.
   - Prefer "I currently have access to..." and "I saw..." over "the full context is...".
   - State that the answer is a human-readable inventory, not a literal context-window dump.
   - Mention that asking for the inventory itself changes the subsequent context.

## Response Template

Use this structure unless the user asks for a different format:

```markdown
**System/Developer Instructions**

[Summarize active high-level behavior rules, tool rules, permissions, sandbox/approval mode, and response constraints.]

**User Conversation**

[Summarize the visible conversation so far in chronological order. Include the current request.]

**Loaded Skills**

[List skills explicitly invoked or read. Mention relevant behavior loaded from each skill.]

**Tool Outputs**

[Summarize important tool calls/results that are still relevant: commands, parsed data, validation output, errors, generated artifacts.]

**Files Read Or Edited**

[List known file paths read, created, or modified. Separate read-only from edited when useful.]

**Environment And Settings**

[List cwd, shell, date/timezone if known, model/settings if visible, approval/sandbox, and other runtime facts.]

**Inferred Or Unknown Parts**

[State what cannot be inspected exactly: hidden platform state, exact full token window, encrypted reasoning, omitted/truncated context, stale metrics, current in-progress work not yet logged.]
```

## Quality Bar

- Be direct and concrete.
- Do not overclaim exactness.
- Include enough detail for a future agent or the user to understand the current state.
- Keep sensitive values out unless the user explicitly asks and they are already visible in context.
