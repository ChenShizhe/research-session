---
name: session-handoff
description: Generate a concise handoff document at the end of a work session so the next session can resume with full context. User-invoked only.
---

# Session Handoff

## Mission

Produce a single `handoff.md` file that captures everything the next work session needs to pick up where this one left off: what was done, what remains, key decisions, and open questions.

## Invocation

This skill is **user-invoked only**. It must never be auto-triggered by other skills or automated pipelines. The user explicitly requests a handoff when they are ending a session.

## Output

The skill writes exactly one file:

- `<project_root>/handoff.md`

Each invocation overwrites the previous handoff for that project. If a running history is needed, the user should archive previous handoffs before invoking.

## Input Contract

| Parameter        | Required | Type   | Description                                                                                          |
| ---------------- | -------- | ------ | ---------------------------------------------------------------------------------------------------- |
| `project_root`   | no       | path   | Absolute path to the project directory. The output `handoff.md` is written here. Defaults to the session's resolved project root when invoked from a research-meeting session. If not provided and no session context exists, ask the user. |
| `project_name`   | yes      | string | Human-readable project name used in the handoff header.                                              |
| `session_number` | no       | int    | Current session number. When omitted, auto-increment from the last handoff found in `project_root`.  |
| `session_label`  | no       | string | Optional short label for this session (e.g. "refactor-auth", "spike-caching"). Used in the heading.  |

### Defaults

- If `session_number` is omitted and no prior `handoff.md` exists, default to `1`.
- If `session_number` is omitted and a prior `handoff.md` exists, parse its session number and increment by one.
- If `session_label` is omitted, the heading uses the session number only.

## Scope

This skill captures session state. It does not:

- Execute remaining work items.
- Modify project files other than `handoff.md`.
- Trigger other skills or pipelines.
- Make decisions about what to do next — it only records the user's stated intentions.

## Behavioral Rules

These rules govern **when and how** the skill executes. They are non-negotiable; violating any of them is an error.

### 1. User-Invoked Only

The skill runs **only when the user explicitly asks** for a handoff. It must never fire automatically — not from hooks, not from other skills, not from pipeline automation. If no explicit user request exists in the current session, the skill does nothing.

### 2. Overwrite, Not Append

Each invocation produces a **complete, self-contained** `handoff.md` that **replaces** the previous version. The new file must carry forward all still-valid decisions, statuses, and task IDs from the prior handoff — nothing is lost — but the mechanism is always a full rewrite, never a patch or append. This ensures every handoff is internally consistent and never accumulates contradictory state.

### 3. Read Before Write

Before generating a new handoff, the skill **must read the existing `handoff.md`** (if one exists) in the target project root. This read is required so the skill can:

- Preserve the global decision numbering sequence.
- Carry forward still-valid pending task IDs.
- Detect and correct stale statuses rather than silently dropping them.

If no prior `handoff.md` exists, this step is a no-op and the skill proceeds with a fresh document.

### 4. Source from Session Context

All content in the handoff must be **derived from the current session's observable context**: the conversation history, the working tree, recent commits, and file state. The skill must not fabricate information, speculate beyond what was discussed or observed, or import content from sources outside the session. If something cannot be verified from session context, it does not belong in the handoff.

---

## Handoff Document Format

The generated `handoff.md` must contain the following sections **in the order listed**. Every required section must be present; omitting one is an error.

### 1. Frontmatter

YAML frontmatter block at the top of the file.

```yaml
---
authored: <ISO-8601 date the handoff was created>
last_updated: <ISO-8601 date the handoff was last modified>
session: <session number, optionally followed by label — e.g. "3" or "3 / refactor-auth">
next_session_starts_here: true
---
```

- `authored` and `last_updated` are always set to the current date/time at generation.
- `session` combines the session number with the optional session label.
- `next_session_starts_here: true` is a fixed flag that lets tooling locate the active handoff.

### 2. What You Are Walking Into

A **3–8 sentence** narrative paragraph that orients the next session. It should answer: What is this project? What phase is it in? What just happened? What is the most important thing to know right now?

Do not use bullet points or tables in this section — write it as prose.

### 3. Current Status

A table summarizing the state of each major work area or component.

| Column   | Description                                                        |
| -------- | ------------------------------------------------------------------ |
| **Item** | The work area, feature, or component.                              |
| **Status** | Current state — e.g. "done", "in progress", "blocked", "not started". |

Example:

```markdown
| Item               | Status      |
| ------------------ | ----------- |
| Auth middleware     | done        |
| Database migration  | in progress |
| API rate limiting   | not started |
```

### 4. Key Decisions Made

A numbered list of decisions, **grouped by session**. Numbers are **globally sequential** across all sessions and **append-only** — earlier decisions must never be renumbered or removed when new sessions are added.

```markdown
#### Session 1
1. Use PostgreSQL instead of SQLite for the backing store.
2. Authentication will be token-based, not session-cookie.

#### Session 2
3. Rate limiting moved to the gateway layer.
```

### 5. Pending Tasks for Next Session

A checklist of tasks remaining, each with a **unique ID** that remains stable across handoff regenerations.

```markdown
- [ ] `T-001` — Write integration tests for the auth endpoint.
- [ ] `T-002` — Migrate staging database to the new schema.
- [x] `T-003` — Update README with setup instructions.
```

IDs use the format `T-NNN` and are never reused. Completed items may remain with a checked box for one handoff cycle to provide context, then should be removed.

### 6. Important Files Reference

A table mapping key files to their purpose.

| Column      | Description                                     |
| ----------- | ----------------------------------------------- |
| **File**    | Relative path from the project root.            |
| **Purpose** | One-line description of why this file matters.  |

Example:

```markdown
| File                        | Purpose                              |
| --------------------------- | ------------------------------------ |
| `src/auth/middleware.ts`    | Token validation and session refresh |
| `migrations/003_add_roles.sql` | Pending role-based access migration |
```

---

## Optional Sections

The following sections **may** be included when they add value. They are placed **after** the required sections, in any order.

### How to Start This Session

Step-by-step instructions for the next session to get into a working state quickly (e.g. which branch to check out, which services to start, which test to run first).

### Notes for the New Agent

Free-form guidance directed at the next agent or collaborator — gotchas, non-obvious context, or warnings about fragile areas.

### Workflow Tracking

Lightweight tracking for multi-step workflows that span sessions (e.g. a migration rollout plan with phases and current phase highlighted).

---

## Prohibited Sections

The following content must **never** appear in a handoff document:

- **Full file contents** — reference files by path, do not embed them.
- **Conversation transcripts** — the handoff is a distilled summary, not a log.
- **Implementation details** — keep the handoff at the "what and why" level, not "how the code works line by line."
- **Speculative future plans** — record only concrete pending tasks and stated intentions, not hypothetical directions.

---

## Formatting Rules

These rules govern the structure and style of every `handoff.md` produced by this skill.

### Markup

Use **Markdown only**. No HTML tags, no embedded images, no raw LaTeX.

### Length Target

Aim for **80–200 lines**. A handoff shorter than 80 lines probably omits critical context; one longer than 200 lines is drifting into documentation territory. If the handoff exceeds 200 lines, split detail into project docs and link to them from the handoff.

### Index, Not Encyclopedia

The handoff is an **index into project state**, not a self-contained encyclopedia. Point to files, commits, and docs by reference — do not reproduce their content. The reader has access to the same repository; the handoff tells them *where to look* and *why it matters*, not *what the code says*.

### Dates

Use **absolute dates** in `YYYY-MM-DD` format everywhere — frontmatter, prose, and task descriptions. Never use relative dates like "yesterday", "last Tuesday", or "next week"; these become meaningless once the session ends.

### No Stale References

Every file path, task ID, and decision reference in the handoff must point to something that currently exists. Before writing the handoff, verify that referenced files are present and referenced task IDs are still valid. Remove or update any reference that has become stale.

### Global Decision Numbering

Decisions in **§ Key Decisions Made** use a single, strictly increasing sequence across all sessions. New decisions append to the end of the list; existing decision numbers are **never reused, renumbered, or removed**. This ensures other documents can cite a decision by its stable number (e.g. "per Decision 4").

---

## Quality Criteria

A handoff document is **good enough** when it satisfies all five criteria below. The overarching test: **a new agent with no prior context can start a productive session from the handoff alone**, without needing to ask clarifying questions or search the repo for orientation.

| #  | Criterion                          | What it means                                                                                                                                   |
| -- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Q1 | **Cold-start ready**               | A new agent reading only the handoff can understand the project's current state, identify the next action, and begin working without extra help. |
| Q2 | **Status table is accurate**       | Every item in the Current Status table reflects the actual state of the codebase right now — nothing is marked "done" that isn't, nothing "in progress" that was finished or abandoned. |
| Q3 | **Pending tasks are actionable**   | Each task in the Pending Tasks list is concrete enough to start immediately: it names what to do, where to do it, and has no unresolved ambiguity. |
| Q4 | **Decisions are traceable**        | Every entry in Key Decisions Made states the decision and enough context that a reader can understand *why* it was made without consulting other sources. Decision numbers are globally stable and sequential. |
| Q5 | **File references are current**    | Every file path in the Important Files Reference (and any inline path elsewhere in the handoff) points to a file that actually exists at the referenced location in the repo. |

### Self-Check Procedure

Before writing `handoff.md`, the agent **must** execute the following self-check. Do not skip steps; do not write the file until every check passes.

1. **Draft the handoff in memory** — assemble all sections mentally or in a scratch buffer before writing to disk.

2. **Q1 — Cold-start test.** Re-read the "What You Are Walking Into" section as if you have zero prior context. Does it answer: what is this project, what phase is it in, what just happened, and what matters most right now? If any answer is missing, revise.

3. **Q2 — Status audit.** For each row in the Current Status table, verify against the working tree or recent commits that the stated status is correct. Fix any row that is stale or wrong.

4. **Q3 — Actionability scan.** For each pending task, confirm it names a concrete action and a target (file, module, endpoint, etc.). If a task says something vague like "finish the feature" or "look into X", rewrite it to be specific.

5. **Q4 — Decision trace check.** For each decision entry, confirm it includes the rationale (the *why*). Confirm the numbering is globally sequential and no numbers were skipped or reused from prior sessions.

6. **Q5 — Path verification.** For every file path in the handoff (Important Files Reference table and any inline references), verify the file exists at that path. Remove or correct any broken reference.

7. **Write the file.** Only after all checks pass, write `handoff.md` to disk.
