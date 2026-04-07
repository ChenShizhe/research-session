---
name: research-meeting
description: Session coordinator for persistent, multi-session research discussions.
version: 1.0.0
---

# Research Meeting

## Mission

Coordinate persistent, multi-session research discussions on a single active project. The skill is responsible for bootstrapping session context at startup, maintaining productive discussion flow throughout, and ensuring all decisions and progress are durably persisted at close. Every session must leave the project in a state where a future session — possibly with no shared context — can resume cleanly.

## Inputs

Logical input fields inferred by the agent from the user's request. These are not a JSON schema — the skill is model-agnostic and does not assume programmatic invocation.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `active_project` | string | yes | — | Research project name. Maps to `~/Documents/Research/<active_project>/`. |
| `session_objective` | string | no | none | What the user wants to accomplish this session. Inferred from opening statement. |
| `agenda_items` | list of strings | no | none | Specific topics. Inferred from user or carried from `tasks.md`. |

### Validation

- `active_project` must correspond to an existing directory under `~/Documents/Research/`. If the directory does not exist, report this and ask whether to create the project scaffold or abort.
- `session_objective` and `agenda_items` are informational. No validation beyond basic presence.

### How inputs are communicated

The user does not fill out a form. Typical invocation patterns:

- "Let's work on the point-process project." — `active_project` resolved from project folder names.
- "I want to discuss the simulation results and plan the next experiment." — `session_objective` and `agenda_items` inferred.
- The agent may ask for clarification if `active_project` is ambiguous (e.g., multiple projects match). This is the only case where the agent asks a question at session start before entering the startup protocol.

## Hard Boundaries

- Do not embed step-by-step procedural instructions in this file. Those live in protocol files under `protocols/`.
- Do not define roles for specialist agents. Those are Phase 4 scope (`roles/`).
- Do not include output format templates. Those are Phase 3+ scope (`templates/`).
- Do not restate general user interaction preferences (conciseness, no unsolicited suggestions, etc.). Those are injected by `memory-retriever` from central memory. Restating them here risks duplication and drift.
- Do not embed memory-retriever logic. It is a separate skill invoked as a dependency.
- Do not embed session-handoff format. It is a separate skill.
- Do not auto-invoke `session-handoff` during close. The user decides when and whether to write a handoff.

## Dependencies

| Dependency | Type | When Invoked |
|------------|------|-------------|
| `memory-retriever` | hard (degraded mode available) | During startup protocol (full context bootstrap) and mid-session (agent-initiated topic-specific recall via `query` parameter, silent to user). |
| `session-handoff` | soft | User-invoked. Close protocol reminds but does not auto-invoke. |
| `experience-logger` | soft | During close protocol — writes session experience log. |
| `research-synthesizer` | soft | During literature pipeline Stage 4 (synthesis). *(Phase 5.)* |
| Scheduling mechanisms | soft | When setting up living review or health digest schedules. *(Phase 5.)* |

Dependencies are referenced by name only. The agent locates and invokes each through the standard skill-discovery mechanism. If a soft dependency is unavailable at runtime, the agent warns and proceeds without it. If `memory-retriever` is unavailable, the startup protocol runs in degraded mode: the core identity pre-flight (Step 1) and memory retrieval (Step 2) are skipped, and the session proceeds with only the project context files from Step 3. The agent warns the user that session context is limited. Core features (discussion, checkpoints, close protocol, specialist initialization) remain fully functional.

## Load Order

### Always load (at skill activation)

1. This file (`SKILL.md`) — read first, keep in context throughout the session.

### Load on demand (routed by session phase)

- `protocols/session-startup.md` — loaded once at session start, then eligible for context eviction after execution.
- `protocols/context-checkpoint.md` — loaded when the user asks to persist mid-session progress.
- `protocols/session-close.md` — loaded once when the session is ending.

Protocol files are designed so that their procedural steps are not needed after execution. The outcomes persist as conversational context, but the step-by-step instructions themselves become eligible for eviction. Runtimes with context compression should treat completed protocol files as low-priority for retention.

## Session Conduct

These directives are always active during a research-meeting session, regardless of phase. They are not routed to sub-files — they live here because they must be loaded once and remembered throughout.

### Context protection

The main agent's context window is sacred. Any task that would require approximately 40 kb or more of context (reading large files, generating lengthy output, literature searches) must be delegated to a subagent. The main agent preserves its context budget for the ongoing research discussion.

### Discussion discipline

Important conclusions and decisions are written to files, not left in chat history. Quick exchanges stay in the conversation; anything that must survive the session is persisted to durable project files. Use the context-checkpoint protocol for mid-session persistence when needed.

### Conversational norms

Research-meeting sessions are collaborative discussions. The general "never end a response with a question" rule from central memory does not apply here — the agent may ask clarifying, confirmatory, or exploratory questions as a natural part of the research conversation. Other central memory interaction preferences (conciseness, no unsolicited suggestions) still apply.

### Subagent trace rule

Every subagent writes a structured output file following `templates/subagent-report.md`. The main agent reads the Executive Summary section only; the full report is available for reference. This keeps subagent results accessible without bloating the main agent's context. Background subagent outputs that remain unreviewed at session close are flagged during the close protocol.

### Pipeline results at startup

If a literature pipeline has active results (discovery queue, completed synthesis), the group lead presents a brief summary during the opening ritual. The full results are in `pipeline/` — do not load them into the main context unless the user asks.

### Health digest at startup

If a recent health digest exists, the group lead reads the "Alerts" and "Suggested Actions" sections and presents them. The full digest stays on disk.

### Voice mode acknowledgment

If the user activates `/voice`, the group lead acknowledges it and reminds the user of the hybrid input norms: speak for discussion, type for equations and code. For the full voice conduct norms, see `protocols/voice-input.md` (norms V1–V4).

### Voice glossary correction (conditional on /voice)

When `/voice` is active and the project has a `voice-glossary.yaml` file, the agent loads the glossary and applies domain vocabulary correction. The correction is a system prompt addition — not a separate preprocessing step. The agent prepends the following instruction block to its working context:

> **Voice glossary active.** The user is dictating via speech-to-text. The following domain terms are frequently mis-transcribed. When the user's input contains a likely mistranscription from this list, silently interpret it as the correct form. Do not ask for confirmation on obvious matches.
>
> Terms are loaded from `~/Documents/Research/<active_project>/voice-glossary.yaml`.

This instruction is loaded only when `/voice` is detected. It is not present in non-voice sessions. See `protocols/voice-input.md` Tier 2 for the full glossary schema and maintenance protocol.

## Protocol Routing

The agent determines the current session phase from conversational context. Phase detection is implicit — there is no explicit `session_phase` parameter.

| Phase | Protocol File | When to Load |
|-------|--------------|--------------|
| startup | `protocols/session-startup.md` | Beginning of session, before any discussion. |
| checkpoint | `protocols/context-checkpoint.md` | When the user asks to persist progress mid-session. |
| close | `protocols/session-close.md` | When the user signals session end, or when the agent determines the agenda is exhausted. |
| delegation | `protocols/subagent-delegation.md` | Before spawning any subagent. |
| multi-agent | `protocols/multi-agent-session.md` | When the user opts in to multi-agent mode. Loaded once at session start alongside startup. *(Opt-in — single-agent is the default.)* |
| specialist-init | `protocols/specialist-initialization.md` | When initializing specialist agents for a multi-agent session. Loaded after multi-agent protocol. |
| pipeline | `protocols/literature-pipeline.md` | When the user requests a literature review run, or when presenting pipeline results at session start. |
| health | `protocols/health-digest.md` | When generating or presenting a health digest. |
| voice | `protocols/voice-input.md` | When voice mode is active (loaded at session start if `/voice` is detected or user mentions voice). |

### Phase transitions

- **Startup → Active discussion:** The startup protocol completes. The agent operates under this file's Session Conduct directives. No additional protocol file is loaded.
- **Startup → Multi-agent init:** When the user opts in to multi-agent mode during startup, the agent loads `protocols/multi-agent-session.md` and then `protocols/specialist-initialization.md` to spawn and initialize specialist agents before entering active discussion.
- **Active discussion → Close:** The user says something like "let's wrap up" or the agent has no more agenda items. The agent loads the close protocol and follows it.
- **Active discussion → Checkpoint:** The user asks to persist progress mid-session. The agent loads the checkpoint protocol, executes it, and returns to active discussion.

When the startup protocol finishes and the agent transitions to active discussion, Session Conduct (this file) is the persistent authority. If any protocol file and Session Conduct give conflicting guidance, Session Conduct takes precedence.

### Multi-agent mode

Multi-agent mode is **opt-in**. The default session mode is single-agent (one group lead, no persistent specialists). The user activates multi-agent mode by requesting it during session startup — for example, "let's run this as a multi-agent session" or "bring in the specialists."

When multi-agent mode is active, the group lead loads the multi-agent session protocol and the specialist initialization protocol in sequence. Specialist role definitions are read from `roles/<specialist-name>.md`.

### Model assignment defaults

When running in multi-agent mode, the following model assignments apply unless the user overrides them:

| Role | Default Model | Rationale |
|------|---------------|-----------|
| Group Lead (Coordinator) | Opus | Best reasoning for synthesis, turn management, and discussion control. |
| Specialists | Sonnet | Good domain reasoning at lower cost. Sufficient context for session-long persistence. |
| One-shot subagents | Sonnet or Haiku | Haiku for exploration/search tasks. Sonnet for reasoning tasks. |

Model names refer to Claude model families. The group lead uses these defaults when constructing specialist initialization prompts. The user may override assignments per-specialist or per-session.

## Project Summary Format (`memory/latest-summary.md`)

The project summary is the project's institutional memory — a single file that captures accumulated understanding across all sessions. It is distinct from the session handoff (which serves onboarding for the next session). The summary is a living document that grows incrementally; the handoff is a disposable snapshot written for the next session's bootstrap.

### Content Schema

The summary contains exactly 7 sections in fixed order. Each has a line budget (soft limit). Exceeding a budget triggers compaction.

| # | Section | Line Budget | Purpose |
|---|---------|-------------|---------|
| 1 | Project Identity | 5–8 | Project name, one-line mission, domain, creation date. Rarely changes after creation. |
| 2 | Architectural State | 10–20 | Current technical architecture, key components, data flow. Updated when architecture changes. |
| 3 | Key Findings | 15–25 | Important research results, validated hypotheses, significant observations. Append-only within a session. |
| 4 | Active Decisions Log | 10–20 | Decisions currently in effect with brief rationale. Superseded decisions are compacted out. |
| 5 | Error Knowledge | 8–15 | Compact index of recurring errors and known failure modes. Two-tier system (see below). |
| 6 | Current State | 5–10 | What was last worked on, what is next, overall project health. Updated every session close. |
| 7 | Open Questions | 5–15 | Unresolved questions, uncertainties, things to investigate. Items are added and resolved over time. |

**Total budget:** ~58–113 lines. Target: under 100 lines for most projects.

All 7 section headers are permanent — they are never removed, reordered, or renamed. An empty section uses `None.` as its sole content line.

### Update Protocol: Anchored Iterative Extension

The project summary is **never rewritten from scratch**. Updates follow the anchored iterative extension protocol:

1. **Read** the existing summary in full before making any changes.
2. **Anchor** on the existing section structure — all 7 section headers are permanent anchors that define the document skeleton.
3. **Identify** which sections need changes based on the current session's outcomes.
4. **Extend** by appending new entries within the appropriate section or updating existing entries in place.
5. **Compact** by removing or condensing entries that are superseded, resolved, or no longer relevant — but only within sections being updated.
6. **Write** the complete file back with the targeted edits applied.

Rules:
- Never delete a section header, even if the section is empty.
- Never reorder sections — the 7-section sequence is fixed.
- Never discard information that has no replacement — if a finding is removed, it must be because a later finding supersedes it.
- Each update pass touches only the sections affected by the current session. Sections with no changes are passed through verbatim.

### Error Knowledge Two-Tier System

Error knowledge uses a two-tier structure to keep the summary compact while preserving full diagnostic context.

**Tier 1 — Summary entries** (in the Error Knowledge section of `memory/latest-summary.md`)

Each entry is a single line:
```
- `<error-id>`: <one-line description> → <resolution or status> [detail: memory/errors/<error-id>.md]
```

The `[detail: ...]` suffix is present only when a Tier 2 file exists.

**Tier 2 — Detail files** (in `memory/errors/`)

Each significant error gets a dedicated file at `memory/errors/<error-id>.md` containing:
- Full error message or stack trace.
- Context: what was being attempted when the error occurred.
- Root cause analysis.
- Resolution steps taken.
- Prevention notes for future sessions.

**Tier rules:**
- Every Tier 2 file must have a corresponding Tier 1 entry. The summary section is the authoritative index.
- Tier 1 entries may exist without a Tier 2 file for trivial or transient errors that did not require investigation.
- A Tier 2 file is created when the error required investigation beyond a simple retry.
- When the Error Knowledge section exceeds its line budget, the oldest resolved entries are removed from Tier 1. Tier 2 detail files are retained for archaeology.
- Error IDs are short, descriptive, kebab-case identifiers (e.g., `latex-bib-missing`, `sim-oom-large-grid`).

### Compaction Rules

Compaction keeps the summary within its line budgets. It is performed during session close (Step 1.7) or during a maintenance session.

**Per-section compaction** — triggered when a section exceeds its line budget by 50% or more:
- Merge redundant entries.
- Remove resolved items from Open Questions and Active Decisions Log.
- Condense Key Findings entries that have been superseded by later findings.
- Archive resolved Error Knowledge Tier 1 entries (Tier 2 files persist).
- Never compact Project Identity — this section is effectively immutable after creation.

**Full compaction** — triggered when the total summary exceeds 120 lines:
- Apply per-section compaction to all sections.
- If still over budget after per-section compaction, recommend a maintenance session.

**Maintenance session triggers** (recommendation, not automatic):
- The summary has exceeded its total line budget for 2+ consecutive session closes.
- The `memory/errors/` directory contains 10+ detail files.
- The user explicitly requests cleanup.

The maintenance session protocol is defined in the Maintenance Session Protocol section below.

## Maintenance Session Protocol

A maintenance session is a special-purpose research-meeting session dedicated to housekeeping rather than research. It restores the project's persistent artifacts to a clean, compact state so that future sessions start efficiently.

### Trigger Conditions

A maintenance session is recommended (never automatic) when any of the following conditions are met:

1. **Consecutive budget overruns** — The project summary (`memory/latest-summary.md`) has exceeded its total line budget (120 lines) for 2 or more consecutive session closes.
2. **Error file accumulation** — The `memory/errors/` directory contains 10 or more Tier 2 detail files.
3. **User request** — The user explicitly asks for a cleanup or maintenance session.

The agent may suggest a maintenance session when it detects condition 1 or 2 during session startup or close. The user decides whether to proceed.

### Protocol Steps

When running a maintenance session, execute the following steps in order:

#### Step 1 — Full Compaction

Apply per-section compaction to all 7 sections of `memory/latest-summary.md`, regardless of whether individual sections have exceeded their budgets:

- Merge redundant entries across all sections.
- Remove resolved items from Open Questions and Active Decisions Log.
- Condense Key Findings entries that have been superseded by later findings.
- Archive resolved Error Knowledge Tier 1 entries (Tier 2 files persist).
- Never compact Project Identity — this section is effectively immutable after creation.
- Target: bring the total summary under 100 lines.

#### Step 2 — Error Index Review

Audit the two-tier error knowledge system:

- Review all Tier 1 entries in the Error Knowledge section. Remove entries for errors that are fully resolved and unlikely to recur.
- Review all Tier 2 files in `memory/errors/`. Flag files whose corresponding Tier 1 entry was removed — these files are retained for archaeology but should not have dangling references.
- Ensure every Tier 2 file has a corresponding Tier 1 entry (or was explicitly archived in Step 1).
- If error files exceed 10, identify candidates for deletion: fully resolved errors with no pattern value. Confirm deletions with the user before proceeding.

#### Step 3 — Open Question Cleanup

Review the Open Questions section of the project summary and all session histories for unresolved questions:

- Resolve questions that have been answered by later sessions (mark as resolved, remove from summary).
- Consolidate duplicate or overlapping questions.
- Re-prioritize remaining questions based on current project direction.
- Move stale questions (unaddressed for 5+ sessions) to a `Parked` annotation at the end of the Open Questions section, or remove them with user confirmation.

#### Step 4 — Memory Promotion Review

Review the project's accumulated knowledge for candidates that should be promoted to central memory:

- Scan Key Findings, Active Decisions, and Error Knowledge for entries that generalize beyond this project.
- Present promotion candidates to the user with a brief rationale for each.
- If the user approves, note the candidates for the memory-management capability to process. The research-meeting skill does not write to central memory directly.

### Session History for Maintenance Sessions

A maintenance session produces a session history like any other session. Use the tag `maintenance` (register it in `sessions/_tags.md` if not already present). The session history records what was compacted, reviewed, cleaned up, and any promotion candidates identified.

### Constraints

- A maintenance session does not advance research. If the user raises a research topic during maintenance, suggest deferring it to the next regular session.
- All compaction and cleanup edits follow the anchored iterative extension protocol — the same update rules that apply to regular session closes.
- Memory promotion is a recommendation step only. This skill identifies candidates; the memory-management capability handles the actual promotion to central memory.

## Session History Format (`sessions/YYYY-MM-DD-NNN.md`)

Session histories are the factual, write-once record of what happened during each research-meeting session. They are distinct from experience logs — session histories capture _what happened_ while experience logs capture _what was learned_. These are fully independent systems; never combine or derive one from the other.

### File Location

Each session history file lives at:

```
~/Documents/Research/<active_project>/sessions/YYYY-MM-DD-NNN.md
```

- `YYYY-MM-DD` — the date the session took place.
- `NNN` — a zero-padded sequence number for the day (e.g., `001`, `002`), allowing multiple sessions per day.

### Frontmatter Schema

Every session history file begins with YAML frontmatter:

```yaml
---
session_id: "YYYY-MM-DD-NNN"
date: YYYY-MM-DD
project: "<active_project>"
session_label: "<brief human-readable label>"
status: "completed" | "interrupted" | "aborted"
tags:
  - <tag>
  - <tag>
---
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | yes | Matches the filename stem. Unique identifier for this session. |
| `date` | date | yes | ISO 8601 date of the session. |
| `project` | string | yes | The `active_project` name. |
| `session_label` | string | yes | Short, human-readable description of the session's focus (e.g., "simulation parameter sweep design"). |
| `status` | enum | yes | One of `completed`, `interrupted`, or `aborted`. `completed` = normal close protocol ran. `interrupted` = session ended before close protocol could finish. `aborted` = session ended before meaningful work occurred. |
| `tags` | list of strings | no | Tags from the tag registry (`sessions/_tags.md`). Used for filtering and retrieval. |

### Required Sections

Every session history file contains these 8 sections in fixed order. An empty section uses `None.` as its sole content line. Section headers are never removed, reordered, or renamed.

| # | Section | Description |
|---|---------|-------------|
| 1 | **Objective** | What the session set out to accomplish. Taken from the opening ritual or user's stated goal. |
| 2 | **Summary** | 2–5 sentence narrative of what actually happened during the session. |
| 3 | **Decisions** | Each decision made, with rationale and any dissenting considerations noted. |
| 4 | **Changes Made** | Files created, modified, or deleted during the session, with brief descriptions. |
| 5 | **Errors Encountered** | Errors that occurred and how they were resolved (or not). References Tier 2 error files if applicable. |
| 6 | **Findings and Insights** | Research observations, results, or conceptual breakthroughs from the session. |
| 7 | **Open Questions** | Questions raised but not resolved during the session. |
| 8 | **Next Steps** | Concrete actions to take in future sessions, derived from this session's work. |

### Optional Sections

These sections are included only when relevant. They appear after the 8 required sections, in the order listed.

| Section | When to Include | Description |
|---------|----------------|-------------|
| **Subagent Dispatches** | When subagents were invoked during the session. | Summary of each subagent dispatch: task delegated, output file path, key results. _(Full subagent dispatch protocol is Phase 3 scope — M7.)_ |
| **Literature Discussed** | When papers, articles, or other literature were referenced or discussed. | Citation keys or references, with brief notes on relevance to the session. |

### Template

```md
---
session_id: "YYYY-MM-DD-NNN"
date: YYYY-MM-DD
project: "<active_project>"
session_label: "<label>"
status: completed
tags:
  - <tag>
---

# Session History — YYYY-MM-DD-NNN

## Objective

<What this session set out to accomplish.>

## Summary

<2–5 sentence narrative of what happened.>

## Decisions

- **Decision:** <what was decided>
  **Rationale:** <why>

## Changes Made

- `path/to/file` — description of change.

## Errors Encountered

None.

## Findings and Insights

- <observation or result>

## Open Questions

- <unresolved question>

## Next Steps

- <concrete action for future sessions>
```

### Tag Registry (`sessions/_tags.md`)

Tags provide a lightweight classification system for filtering and retrieving session histories. All tags used in session frontmatter must be registered in `sessions/_tags.md`.

The tag registry file lives at:

```
~/Documents/Research/<active_project>/sessions/_tags.md
```

#### Registry Format

```md
# Session Tags

## Domain Tags
- `<tag-name>` — <one-line description>

## Activity Tags
- `<tag-name>` — <one-line description>

## Status Tags
- `<tag-name>` — <one-line description>
```

#### Registry Rules

- Tags are lowercase, kebab-case identifiers (e.g., `simulation-design`, `literature-review`, `bug-fix`).
- Every tag has a one-line description explaining when to apply it.
- Tags are organized into three categories:
  - **Domain tags** — the research topic or subarea (e.g., `point-process`, `bayesian-inference`).
  - **Activity tags** — what kind of work was done (e.g., `experiment-design`, `data-analysis`, `code-review`, `literature-review`).
  - **Status tags** — session outcome signals (e.g., `breakthrough`, `blocked`, `routine`).
- New tags may be added at any time by appending to the appropriate category. Tags are never removed — only deprecated by adding `(deprecated)` to the description.
- A session should use 1–5 tags. Prefer specificity over exhaustiveness.

### Write-Once Immutability

Session history files are **write-once**: once a session history is written during the close protocol, its content is considered immutable. This ensures that session histories are a reliable, tamper-evident record of what happened.

#### Post-Session Correction Exception

The sole exception to write-once immutability is **post-session corrections**, which are permitted under these conditions:

1. **Factual error** — the session history contains a demonstrably incorrect statement of fact (e.g., a wrong file path, a misattributed decision, an incorrect date).
2. **Correction, not revision** — the change corrects a factual error. It does not add new information, reinterpret decisions, or revise the narrative with hindsight.
3. **Correction block** — every correction is appended as a clearly marked correction block at the end of the file, preserving the original text:

```md
---

## Corrections

- **Corrected YYYY-MM-DD:** <section> — <what was wrong> → <what is correct>.
```

4. **Original text preserved** — the original text in the body is not modified. The correction block serves as an erratum that readers apply mentally. This preserves the write-once property of the original content while allowing factual errors to be flagged.

#### What is NOT a valid correction

- Adding information that was omitted from the original session history.
- Rewriting a decision's rationale based on later outcomes.
- Changing tags or session_label after the fact (unless the original was factually wrong).
- Any change motivated by "we now know better" rather than "this was wrong at the time."
