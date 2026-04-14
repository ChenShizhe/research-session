# Session Startup Protocol

## Purpose

Bring the agent from zero context to a state where it can hold a productive research discussion on the active project. After startup completes, the agent should know:

- Who it is and how to behave (core identity).
- What the project is about (domain context).
- What happened in prior sessions (continuity).
- What tasks are pending (agenda source).
- What the user wants to do this session (objective).

---

## Canonical Startup Step Table (All Phases)

This table establishes the authoritative step numbering. All protocol amendments reference these step numbers. Steps are listed in execution order. Steps marked with a phase are only executed when that phase's features are active.

```
Phase 1 (P1-D2):
  Step 1:  Pre-flight — read core identity files (AGENTS.md, SOUL.md, IDENTITY.md, USER.md)
  Step 2:  Invoke memory-retriever (project_root, session_phase=start)
  Step 3:  Read project context — domain-prior.md, roadmap.md, latest-summary.md (P2),
           tasks.md, handoff.md, latest-expanded-instruction.md
  Step 4:  Staleness check — report handoff last_updated date to user
  Step 5:  Opening ritual — present project name/phase, pending tasks, new subagent outputs;
           ask "What has changed since the last session?"

Phase 5 (P5-D5) — lightweight checks, all steps optional:
  Step 5a: Health digest check — read latest digest, present alerts if < 7 days old
  Step 5b: Discovery queue check — present new papers from living review
  Step 5c: Pipeline checkpoint check — surface unreviewed checkpoints
  Step 5d: Voice mode detection — acknowledge /voice, load glossary if Tier 2 configured

Phase 4 (P4-D4) — only in multi-agent sessions:
  Step 6:  Roster selection — determine which specialists to activate
  Step 7:  Workspace preparation — create/update workspace/, write agenda.md
  Step 8:  Specialist spawning — spawn all selected specialists in parallel
  Step 9:  Readiness barrier — wait for specialists to signal readiness (3-min timeout)
  Step 10: Opening broadcast — welcome team, set first topic

Transition:
  Step 11: Active discussion begins (governed by SKILL.md Session Conduct)
```

**Notes:**
- P1-D2 Steps 1-5 always execute. P2-D3 amendments (latest-summary.md in Step 3, enhanced question in Step 5) are incorporated into the base steps.
- P3-D3's close protocol extension (check for unreviewed subagent outputs) is part of P1-D2 Step 5's substep (checking `subagent-outputs/` directory).
- Phase 5 steps (5a-5d) are skipped if no Phase 5 features are configured for the project.
- Phase 4 steps (6-10) are skipped in single-agent sessions.

---

## Steps

### Step 1: Pre-flight — Core Identity

Read in this exact order:

1. `~/Documents/memory/AGENTS.md`
2. `~/Documents/memory/SOUL.md`
3. `~/Documents/memory/IDENTITY.md`
4. `~/Documents/memory/USER.md`

These are read unconditionally, every session. This step is required by AGENTS.md and is independent of `memory-retriever`. If `memory-retriever` also injects core files, the redundancy is harmless.

**Failure handling:**

- `AGENTS.md` missing or unreadable — **abort startup**. Report to user: "Core agent protocol file is missing. Cannot start session."
- Any other core file missing — **warn and continue**. Report which file is missing. Proceed with partial core identity.

### Step 2: Invoke Memory-Retriever

Invoke `memory-retriever` with:

- `active_project`: the resolved project name (from SKILL.md input contract).
- `session_phase`: `start`
- `retrieval_round_mode`: determined by `memory-retriever`'s auto-detection.

This step retrieves project-specific memory, prior session context, and any relevant catalog-derived memory cards. The output is written to the project's `memory/latest-expanded-instruction.md`.

**Failure handling:**

- `memory-retriever` is unavailable (skill not found) — **warn and continue in degraded mode**. Report: "memory-retriever skill is not available. Session context will be limited to project files only." Skip to Step 3.
- `memory-retriever` runs but reports partial failures (fail-loud) — **continue**. Note which memories were unavailable and proceed. The user sees the failure report.

### Step 3: Read Project Context

Read the following files from the project root (`<project_root>/`, resolved at session start per SKILL.md § Project Root Resolution):

1. `domain-prior.md` — required for first-session orientation; may not exist for brand-new projects.
2. `roadmap.md` (or `grand-plan.md`) — project-level roadmap, if it exists. Read if present; skip silently if not.
3. `memory/latest-summary.md` — project summary produced by the memory system. Provides a high-level snapshot of project direction, key decisions, and accumulated context. Read if present; skip silently if not.
4. `tasks.md` — running task checklist. May not exist for brand-new projects.
5. `handoff.md` — if present, contains prior session state and pending work. The handoff acts as an index pointing to other files rather than embedding their content. Follow its references to load what is needed.
6. `memory/latest-expanded-instruction.md` — the output from Step 2.

Read order matters: domain-prior and roadmap provide conceptual grounding before tasks and handoff provide operational state.

**Failure handling:**

- `domain-prior.md` missing — **warn and continue**. Note: "No domain prior found. This may be a new project or the file hasn't been created yet."
- `roadmap.md` missing — **continue silently**. Not all projects have a roadmap.
- `memory/latest-summary.md` missing — **continue silently**. The summary is generated by the memory system and may not exist for new projects or if the summary pipeline has not yet run.
- `tasks.md` missing — **continue silently**. Not unusual for new projects.
- `handoff.md` missing — **continue silently**. Absence is a valid signal (new project or fresh start).

### Step 4: Staleness Check

If `handoff.md` exists, report its `last_updated` date to the user. Example: "Handoff was last updated on 2026-03-30 (today / 3 days ago / 2 weeks ago)."

The agent does not autonomously decide whether a handoff is stale. The user confirms or overrides. If the user says the handoff is outdated, proceed as if no handoff exists (full bootstrap context, not incremental).

This step is a brief inline report, not a separate protocol.

### Step 5: Opening Ritual

Present to the user:

1. **Project name and phase** — what phase the project is in per roadmap or handoff.
2. **Project summary highlights** — if `memory/latest-summary.md` was loaded, present a brief (2-4 bullet) digest of its key points: overall project direction, major decisions, and any flagged risks or open questions. This gives the user a quick orientation before diving into tasks.
3. **Pending tasks** — from `tasks.md` and/or handoff, summarized concisely.
4. **Subagent outputs** — check `subagent-outputs/` directory. If any new files exist since the last session, list them.

Then ask: **"What has changed since the last session, and is the project still heading in the direction described in the summary?"**

This question is permitted — research-meeting sessions override the "no questions" rule. The user's answer updates the agent's understanding before discussion begins.

### Step 5a: Health Digest Check

*Phase 5 (P5-D5) — lightweight check, optional. Skipped if no Phase 5 features are configured.*

```
If <project_root>/digests/ exists:
  Read the most recent digest file (by date in filename).
  If digest is < 7 days old:
    Present the "Status at a Glance" and "Alerts" sections to the user.
    Mention: "Full digest available at digests/YYYY-MM-DD.md"
  If digest is > 7 days old or missing:
    Note: "No recent health digest. Consider running one or scheduling
    via local task scheduler."
```

This is a lightweight check — read one file's header. The full digest is not loaded into context. See P5-D3 Section 8 for full integration details.

### Step 5b: Discovery Queue Check

*Phase 5 (P5-D5) — lightweight check, optional. Skipped if no Phase 5 features are configured.*

```
If <project_root>/pipeline/discovery-queue.md exists and is non-empty:
  Read the summary section (paper count and last run date).
  Present: "Living review found N new papers since [date]. Review them now or later?"
  If user says "now": load protocols/literature-pipeline.md and begin screening.
  If user says "later": continue to opening discussion.
```

### Step 5c: Pipeline Checkpoint Check

*Phase 5 (P5-D5) — lightweight check, optional. Skipped if no Phase 5 features are configured.*

```
If <project_root>/pipeline/checkpoints/ has unreviewed checkpoints:
  Present: "A pipeline checkpoint awaits your review: [checkpoint type] from [date]."
  Offer to present the checkpoint for review.
```

Unreviewed checkpoints are identified by the absence of a corresponding `reviewed: true` marker in the checkpoint file's frontmatter.

### Step 5d: Voice Mode Detection

*Phase 5 (P5-D5) — lightweight check, optional. Skipped if no Phase 5 features are configured.*

```
If the user has activated /voice (detectable from session state):
  Acknowledge: "Voice mode active. Reminder: speak for discussion, type for
  equations and code. Domain glossary loaded for [project-name]."
  Load protocols/voice-input.md if Tier 2 correction is configured.
```

If Tier 2 voice glossary correction is configured, load the project's `voice-glossary.yaml` and inject its terms into the system prompt for transcription correction (~300-500 tokens). See `protocols/voice-input.md` for full glossary correction protocol.

### Step 6: Transition to Active Discussion

Once the user responds to the opening ritual and any Phase 5 checks have been presented, the startup protocol is complete. The agent transitions to operating under SKILL.md's Session Conduct directives. The startup protocol's procedural steps are no longer needed in active context and become eligible for context eviction.

In multi-agent sessions, Phase 4 steps (roster selection, workspace preparation, specialist spawning, readiness barrier, and opening broadcast) execute between Step 5d and this transition. See P4-D4 for details.

---

## Edge Cases

### E1: Brand-new project (no prior sessions)

- No `handoff.md`, no `tasks.md`, no `domain-prior.md`, no `sessions/` directory.
- `memory-retriever` does full bootstrap (auto-detected from absence of handoff).
- Steps 1-2 complete normally. Step 3 finds nothing. Step 4 is skipped.
- Step 5 reports: "This appears to be the first session for this project. No prior tasks or session history found."
- Steps 5a-5d are all skipped (no digests, no pipeline, no voice config for a new project).
- The agent asks what the project is about and what the first session objective is. This information becomes the basis for creating `domain-prior.md` and `tasks.md` during the session or at close.

### E2: User provides a project name that doesn't exist

Handled before the startup protocol begins, at the SKILL.md input validation level: the agent reports the directory doesn't exist and asks whether to create the project scaffold or abort.

### E3: Multiple projects could match the user's description

Handled at SKILL.md input validation level: the agent lists matches and asks for clarification. Asking is always safer than guessing.

### E4: Handoff exists but is clearly outdated (months old)

Step 4 reports the date. The user decides whether it is still relevant. The agent does not apply arbitrary staleness thresholds.

### E5: Memory-retriever returns a very large expanded instruction

The context protection rule (~40 kb threshold) applies to mid-session tasks, not to startup. Startup inherently loads substantial context. If the expanded instruction is unusually large, the agent notes this but does not truncate — the user has final say on what to trim.

### E6: Phase 5 features partially configured

A project may have a health digest but no pipeline, or vice versa. Each Phase 5 step (5a-5d) operates independently. Missing directories or files cause the step to be silently skipped — no errors, no warnings for unconfigured features.
