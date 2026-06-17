---
name: hand-holding
description: Strict explicit-invocation-only snippet-by-snippet coding workflow. Use this skill only when the user includes the exact token `$hand-holding` or explicitly says to use the exact hyphenated `hand-holding` skill while asking Codex to write, edit, refactor, debug, or test code. Do not use for ordinary coding requests, ordinary code reviews, PR reviews, audits, teaching requests, mentoring requests, requests for "hand holding" without the hyphen, or any semantically similar phrasing unless the exact `$hand-holding` or `hand-holding` invocation appears. When used, present big architecture/code-shape decisions first, then propose implementation as many tiny reviewable code snippets of a few lines each so the user can guide syntax, style, naming, structure, and implementation details before code is applied.
---

# Hand-Holding

## Overview

Use this skill to make the user an active reviewer of how code is written. Draft the solution internally, but expose it as architecture decisions followed by small code snippets so the user can steer syntax, naming, structure, and implementation details before the code lands.

## Hard Rules

- Treat explicit user guidance as the control loop. End every architecture decision and every code snippet with a clear question, then wait for the user's answer before applying it.
- Do not apply code changes before the user approves the overall plan and the specific snippets being applied, unless the user explicitly asks to skip snippet review.
- Approval to create a file, class, component, or function approves only that container. It does not approve the implementation body inside it.
- Never write a large unreviewed implementation after a broad approval. Split all substantive code into as many snippets as needed.
- Keep snippets small by default: usually 3-12 lines, and rarely more than 20 lines unless the user explicitly approves a larger block.
- Prefer more snippets over fewer snippets when syntax, naming, control flow, or structure could benefit from user preference.
- Keep hidden implementation reasoning private. Share concise rationale, tradeoffs, file targets, and proposed code shape rather than chain-of-thought.
- If the user changes direction, revise the remaining plan and continue from the current code state.
- Treat a reply like "yes", "approved", "go ahead", or "apply it" as approval for the current decision or snippet only unless the user clearly grants broader approval.
- If the user says "continue" or grants broader approval, still stop at the next big architecture choice or style-sensitive implementation pattern.

## Workflow

1. Inspect the codebase enough to understand the current patterns, ownership boundaries, tests, and likely files to touch.
2. Present big decisions before editing. Include:
   - the user-visible goal,
   - the likely files/modules involved,
   - the proposed architecture or code-shape options,
   - the sequence of snippet groups to review,
   - the first decision needed from the user.
3. Wait for the user's approval or adjustments to the big decisions.
4. For each snippet group, propose one small code snippet at a time:
   - state the target file and insertion/replacement location,
   - show the exact snippet or a near-exact diff preview,
   - explain the style or implementation choice in one short sentence,
   - ask whether to apply, revise, or reject it.
5. After approval, apply only the approved snippet. Do not include later snippets in the same edit.
6. Summarize the applied snippet in one sentence, then present the next snippet.
7. Repeat until all code, tests, and cleanup are reviewed and applied.
8. Run the strongest reasonable final verification for the task.
9. Finish with a short summary of implemented changes, validations run, and any remaining risks or follow-ups.

## Snippet Boundaries

Split implementation around choices the user can review:

- File creation and imports.
- Constants, configuration, variables, and state declarations.
- Types, interfaces, schemas, and data structures.
- Function signatures before function bodies.
- Each helper function body.
- Each branch of non-trivial control flow.
- Each event handler, route handler, API call, or public method.
- UI markup/structure before styling.
- Styling blocks after structure.
- Tests, fixtures, and assertions in focused chunks.

Avoid arbitrary line-count splitting, but never use that as a reason to batch a large implementation. If a complete idea is larger than 20 lines, split it into reviewed subparts such as setup, validation, core logic, and return/output handling.

## User Prompts

Use short, explicit prompts at each pause:

- "Approve this architecture direction, or change the structure before we write snippets?"
- "Approve this snippet, revise the syntax/naming, or reject this approach?"
- "This only creates the file shell. The implementation body will come in separate snippets."
- "Do you want this as a helper, inline code, or a different shape?"
- "The next checkpoint is tests. Should I add focused unit coverage, integration coverage, or both?"

## Applying Changes

When a snippet is approved:

- Use the repository's normal editing and formatting tools.
- Apply only the approved snippet or the smallest mechanical edit needed to place it correctly.
- Do not mix unrelated future snippets into the current patch.
- If formatting changes surrounding lines, report that separately.
- If validation fails, explain the failure, propose a repair snippet, and wait if the repair involves a design or style choice.
- If a fix is mechanical and clearly within the approved snippet, apply it and report it.
