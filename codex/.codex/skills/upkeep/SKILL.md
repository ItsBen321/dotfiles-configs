---
name: upkeep
description: Explicit-invocation-only project upkeep driven by user-defined subject files in the current project's .upkeep directory. Use only when the user invokes `$upkeep` or explicitly asks to use the upkeep skill to configure or perform project upkeep; never trigger it implicitly for ordinary maintenance, refactoring, dependency, documentation, or cleanup requests.
---

# Upkeep

Maintain every user-configured upkeep subject in the current project. Treat `.upkeep/*.md` as concise, persistent instructions and status documents, and as the authority boundary for project edits.

## Resolve the project

1. Resolve the project root from the current working directory. Prefer the enclosing Git worktree root; otherwise use the current working directory.
2. Use only `<project-root>/.upkeep/`. Do not reuse upkeep configuration from another project or a parent directory outside the resolved project.
3. Inspect the working tree before editing. Preserve unrelated user changes and stop for direction if they overlap required upkeep work.

## Set up an unconfigured project

Treat a missing `.upkeep/` directory, an empty directory, or a directory with no subject Markdown files as unconfigured.

1. Tell the user that project upkeep must be configured.
2. Ask the user to name the upkeep subjects. Do not suggest, infer, or create subjects.
3. For every named subject, obtain:
   - the project paths that changes may touch;
   - what the subject is responsible for and how it works;
   - what healthy/current means;
   - what recurring upkeep should check or do;
   - any subject-specific validation commands or constraints.
4. Ask concise follow-up questions only for missing information. Read-only project inspection may help document a user-named subject, but it must not invent more subjects or broaden the user's scope.
5. Create `.upkeep/` after the user confirms at least one subject and its scope. Create one lowercase hyphenated Markdown filename per subject.
6. Do not perform project upkeep during initial configuration unless the user also asks to continue after reviewing the created subject files.

Use this compact format for new subject files and preserve equivalent existing formats:

```markdown
# Subject name

## Scope
- `path/or/pattern`: reason it is in scope

## Current state
Short description of the present condition and last known result.

## Structure
Short description of how the subject works and where its important pieces live.

## Upkeep
- Concrete check or action.

## Last run
- Never, or YYYY-MM-DD: concise outcome and remaining work.
```

Keep each file operational and short. Replace stale status rather than accumulating an unbounded history.

## Perform upkeep

1. Read every `.upkeep/*.md` subject file before changing the project.
2. Process every subject on every invocation. For each subject, inspect its declared scope and compare the project with its current-state, structure, and upkeep instructions.
3. Perform necessary changes within the declared scope. A subject may be skipped only when inspection gives a concrete reason that no upkeep is needed.
4. Run proportionate validation, favoring commands named by the subject file. Do not claim success when validation was not run or failed.
5. Update every subject file after processing it, including skipped or blocked subjects. Refresh current state, structure when it changed, and the single last-run entry. Record changed paths, validation, skip reason, or blocker concisely.
6. Report the outcome per subject and list any approvals or follow-up work still needed.

## Scope and approval boundaries

- Treat the paths in each subject's `Scope` section as the allowed edit boundary for that subject. Do not interpret a subject name or prose description as permission to edit additional paths.
- Read outside the declared scope only as needed to understand dependencies and impact; reading does not expand edit authority.
- Before creating or modifying any project file outside all applicable subject scopes, explain why it is needed and ask the user for approval. This specifically includes helper, migration, build, or automation scripts created to make upkeep work.
- If the user approves a path as recurring scope, update the relevant subject file before editing that path. For one-time approval, record the exception in `Last run` without silently broadening future scope.
- Ask before running a command expected to rewrite project files outside the declared scope. Standard read-only checks are allowed.
- Do not delete data, make major dependency upgrades, commit, push, publish, deploy, or modify external systems unless the user explicitly authorizes that action.
- Do not change a subject's purpose, remove a subject, or add a subject without the user's explicit direction.
- Keep fixes minimal and directly tied to the written upkeep instructions. Do not bundle opportunistic refactors or cleanup.

## Incomplete configuration

If a subject file lacks an actionable scope or upkeep instructions, do not guess. Ask the user for the missing information, continue with other complete subjects when safe, and mark the incomplete subject as blocked rather than maintained.
