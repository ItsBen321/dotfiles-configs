# Vault Update Rules

Use this reference when adding, editing, splitting, or reorganizing the game-design vault.

## Update When

Add durable memory when it is likely to improve future game-design answers:

- The user states a recurring design preference, dislike, constraint, taste, or priority.
- A concept gains a stable pitch, target experience, core loop, pillar, risk, or decision.
- A brainstorm produces reusable mechanic patterns, prompt banks, or strong idea seeds.
- A critique identifies a generalizable design risk or anti-pattern.
- Research produces a durable lens, source, case study, accessibility rule, playtest method, or genre/system pattern.
- A playtest produces findings, hypotheses, observed player behavior, or next design decisions.
- A vault navigation problem is discovered, such as missing routes, oversized notes, duplicate concepts, or broken links.

## Do Not Update For

- One-off chat phrasing that is not a durable preference.
- Raw logs, long transcripts, or full article dumps.
- Implementation details unless they constrain design feasibility.
- Unsupported guesses written as facts.
- Generic advice already covered by an existing note.
- Temporary discarded ideas unless they explain a meaningful decision.

## Where To Put Updates

- User preference: `Preferences/`.
- New or evolving game idea: `Concepts/` until a dedicated concept/project structure exists.
- Reusable concept-generation material: `Concepts/Mechanic Prompt Bank.md` or a new focused concept note.
- Design principles and frameworks: `Foundations/` or `Design Lenses/`.
- Balance, progression, randomness, social, procedural, or economy material: `Systems/`.
- Genre-specific guidance: `Genres/`.
- Onboarding, readability, assist modes, or feel: `UX and Onboarding/`.
- Research summaries and source maps: `Source Notes/`.
- Specific examples from shipped games: `Case Studies/`.
- Agent-facing process, audits, routing, or maintenance: `Agent Guides/`.
- Output structures: `Templates/` or `Examples/`.

## Update Shape

Prefer small, atomic edits:

1. Update an existing note when the new information strengthens the same topic.
2. Create a new note when the topic would make the existing note mixed-purpose or hard to scan.
3. Link the new note from `INDEX.md` or `Agent Guides/Agent Routing Guide.md` if future agents should find it directly.
4. Add source URLs in frontmatter and/or the source note.
5. Mark speculation as `draft`, `hypothesis`, or `open question`.
6. Keep the actionable rule near the top of the note.

## Conflict Rules

When notes disagree, use this priority order:

1. The user's latest direct instruction.
2. Active concept/project-specific notes.
3. Active user preference notes.
4. Active playtest findings.
5. Source-backed framework and case-study notes.
6. Draft notes, speculative ideas, and general prompts.

Mention unresolved conflicts briefly in the user-facing answer instead of silently choosing a weak assumption.

## Quality Bar

A useful vault update should answer at least one of these questions for a future agent:

- What should I read first?
- What does the user prefer?
- What decision has already been made?
- What design risk has already been noticed?
- What source supports this lens?
- What concrete example should I imitate or avoid?
- What playtest result changes the next design step?

## Maintenance Checks

After meaningful vault edits:

- Run the vault search helper with `-Overview` for a fast sanity check.
- Check that new notes are linked from an index or routing note.
- Check for broken `[[links]]` when adding many links.
- Keep long notes split by responsibility. If a note is becoming an archive, create a short routing note and move detail into linked notes.

