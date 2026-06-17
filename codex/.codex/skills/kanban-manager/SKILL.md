---
name: kanban-manager
description: Maintain a user-specified Obsidian Kanban board or markdown task board. Use when the user provides a board file/path and asks Codex to review, prioritize, split, rephrase, reorganize, add, move, archive, or clean up tasks.
---

# Kanban Manager

Use this skill to keep a user-specified kanban board organized and actionable.

## Target Board

- Require the user to provide the board file or an unambiguous path each time.
- Accept absolute paths, workspace-relative paths, attached files, or a clearly named file in the current workspace.
- If the request does not identify a specific board, ask for the board file/path before reading or editing anything.
- If multiple candidate files match, list the candidates and ask the user which board to use.
- Do not assume a default project, vault, or board from prior conversations.
- Confirm the resolved board path before making edits when the path was inferred rather than explicitly provided.

## Board Expectations

- The board may use the Obsidian Kanban plugin format or a plain markdown task-board format.
- Preserve the note's frontmatter, checklist syntax, and kanban settings block.
- Treat each `##` heading as a board column unless the user asks to restructure the board.
- Preserve comments, tags, block IDs, embeds, links, dates, priorities, and plugin-specific markers unless the user asks to change them.
- Match the board's existing conventions for completed tasks, subtasks, indentation, tags, due dates, and archived sections.

## Workflow

1. Resolve the target board from the user-provided file or path.
2. Read the current board before making changes.
3. Identify the board structure: frontmatter, settings block, columns, archived/completed sections, card syntax, and any local conventions.
4. Review tasks for priority, dependencies, duplicates, urgency, blockers, ownership, and scope.
5. Reorder tasks so the most urgent or highest-leverage work appears first within the appropriate column.
6. Rewrite vague items into concrete, actionable tasks while preserving the user's intent.
7. Break large or ambiguous work into smaller checklist items when the next steps are reasonably clear.
8. Move tasks between columns only when their state or scope clearly suggests a better location, or when the user explicitly asks.
9. Summarize the changes after editing the board, including the board path used.

## Guardrails

- Keep completed items and archive history unless the user asks to prune them.
- Prefer minimal edits that improve clarity over speculative rewrites.
- Add new tasks only when the user asks for them or they are directly implied by an existing item or dependency.
- Ask the user when prioritization depends on product intent, design choices, or unclear tradeoffs.
- Keep wording short and specific; each card should describe one clear piece of work.
- Do not silently convert between incompatible kanban formats.
- Do not modify unrelated notes in the same vault or folder unless the user explicitly asks.
- Avoid broad taxonomy rewrites unless the user asks to restructure the board.
