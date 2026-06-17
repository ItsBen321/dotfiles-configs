---
name: git-log
description: "Analyze git changes in the active project repository, split them into focused commits by default, write concise commit titles and descriptions, and optionally write a local changelog entry when the user asks or the destination is already known. Use when Codex needs to review local repo changes, prepare commit text, commit work, or document project changes."
---

# Git Log

## Workflow
- Use the git repository for the active project or current working directory unless the user specifies another repo.
- If the current directory is not inside a git repository, look for the nearest relevant project repo from context; if none is clear, ask the user for the repo path.
- Inspect staged, unstaged, and untracked changes before writing any summary.
- Derive all wording from the actual diff. Do not invent intent or features that are not visible in the changes.
- Create a commit plan before staging or committing. The plan must list each proposed commit, its files or hunks, and the reason those changes belong together.
- Split changes into multiple focused commits by default. Each commit must represent one coherent behavior, fix, refactor, documentation update, asset change, or tooling change.
- Prefer smaller commits whenever two changes can be understood, reverted, tested, or reviewed independently.
- Make a single commit only when the user explicitly asks for one large commit, or when the inspected diff is genuinely indivisible. If using one commit because the diff is indivisible, state that rationale before committing.
- If the correct split is ambiguous, propose the smallest sensible commit groups and ask the user to choose before staging.
- Use partial staging (`git add -p`, pathspecs, or equivalent) when one file contains changes for multiple commit groups.
- For each commit, write commit content with:
  - A short, precise title.
  - A short description with a hard maximum of 300 characters.
  - A bullet list of the notable changes.
- Stage the files that belong in the commit unless the user explicitly asks to leave staging unchanged.
- Commit each change set using the prepared title and description.

## Optional local changelog
- Add or update a local changelog file only when the user asks for it or when a changelog destination is already known from context.
- Use the changelog file in the active project unless the user specifies another location.
- Match the existing changelog style if the file already has a clear format.
- If there is no obvious established format, use:

```md
## <commit title>
Date: <local date and time>
Commit: <short hash>
Summary: <short description>
Stats: <files changed / insertions / deletions>

- <notable change 1>
- <notable change 2>
```

## Data to record
- When writing a local changelog entry, record the local date and time of each commit.
- Record the commit hash after creating each commit.
- Record the amount of change using git statistics such as files changed, insertions, deletions, or the closest reliable summary available.

## Guardrails
- Keep titles and summaries compact and factual.
- Prefer user-facing impact first, then technical cleanup.
- Keep bullets specific enough that the log is useful weeks later.
- Avoid noisy details such as trivial formatting-only edits unless they materially affect the change set.
- Do not push, merge, or open a pull request unless the user explicitly confirms.
- After committing, ask whether the user also wants to push the branch. If the context includes a pull request, release branch, or merge target, also ask whether they want to merge.
