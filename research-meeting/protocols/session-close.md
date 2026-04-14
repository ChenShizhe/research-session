# Session Close Protocol

## Purpose

Ensure that all work done during the session is persisted and that the next session can resume cleanly. The close protocol writes durable artifacts; anything not written down is lost.

## Trigger

The close protocol is loaded when:

- The user signals session end ("let's wrap up," "that's it for today," "okay we're done").
- The agent determines the agenda is exhausted and there is nothing productive left to discuss.

---

## Canonical Close Step Table (All Phases)

This table establishes the authoritative step numbering. All protocol amendments reference these step numbers. Steps are listed in execution order. Steps marked with a phase are only executed when that phase's features are active.

```
Adjournment (P4-D4) — only in multi-agent sessions:
  Step A1: User departs — no new tasks
  Step A2: Specialists finish in-progress work
  Step A3: Group lead monitors with check-ins
  Step A4: Specialist close summaries
  Step A5: Group lead synthesis
  Step A6: Workspace finalization
  Step A7: Specialists dismissed

Standard Close Sequence:
  Step 0:   Confirm intent
  Step 1:   Update tasks.md
  Step 1.3: Check for unreviewed subagent outputs
  Step 1.5: Write session history
  Step 1.7: Update project summary (latest-summary.md)
  Step 2:   Remind about session-handoff
  Step 3:   Run experience-logger
  Step 3.3: Digest update consideration (P5-D5, conditional)
  Step 3.5: Central memory promotion reminder (conditional)
  Step 3.7: Glossary maintenance (P5-D5, optional)
  Step 4:   Final summary — includes pipeline state report
```

**Notes:**
- Adjournment steps (A1-A7) execute only in multi-agent sessions, before the standard close sequence.
- P5-D5 steps (3.3, 3.7) are skipped if no Phase 5 features are configured for the project.
- Step 1.5 (session history) now includes an optional Pipeline State section when Phase 5 pipeline features are active.
- Step 4 (final summary) now includes pipeline state in its output when Phase 5 pipeline features are active.

---

## Meeting Adjournment Phase

When the session involves a multi-specialist research meeting (group lead plus specialists), the adjournment phase handles the transition from active meeting to session close. These steps execute **before** the standard close sequence below.

### Step A1: User Departs — No New Tasks

The user signals departure and confirms no additional tasks will be assigned. The group lead acknowledges the departure and shifts into adjournment mode. No new work items are accepted after this point.

### Step A2: Specialists Finish In-Progress Work

Each specialist completes any work that is actively in progress. Work that cannot be finished in a reasonable time frame is wrapped to a safe stopping point and noted as incomplete. No new work is started.

### Step A3: Group Lead Monitors with Check-Ins

The group lead monitors specialist progress with approximately 15-minute check-ins. During each check-in:

- Confirm the specialist's remaining work and estimated time to completion.
- Identify any blockers that could prevent clean wrap-up.
- Adjust priorities if a specialist is running long — prefer a clean partial result over a rushed complete one.

### Step A4: Specialist Close Summaries

Once a specialist finishes their in-progress work, they produce a close summary covering:

- **Work completed** — what was accomplished during the session.
- **Work remaining** — anything left unfinished, with enough context to resume.
- **Key findings** — notable results, observations, or surprises.
- **Open questions** — unresolved questions surfaced during the work.

Each specialist delivers their close summary to the group lead.

### Step A5: Group Lead Synthesis

The group lead synthesizes all specialist close summaries into a unified session account:

- Consolidate findings across specialists, noting connections and contradictions.
- Merge open questions, de-duplicating where specialists raised the same issue.
- Identify cross-cutting themes or emergent insights that no single specialist would see alone.
- Flag any items that need user attention at the next session.

### Step A6: Workspace Finalization

The group lead ensures the workspace reflects the session's outcomes:

- Update `findings.md` with new findings from specialist close summaries and the group synthesis.
- Update `questions.md` with open questions surfaced during the session.
- Verify that all specialist-produced artifacts are saved and correctly located.
- Confirm no temporary or draft files remain that should have been finalized or removed.

### Step A7: Specialists Dismissed

The group lead confirms all specialist work is complete and summaries have been received, then formally dismisses the specialists. After dismissal, only the group lead (or main agent) continues into the standard close sequence.

---

## Standard Close Sequence

The following steps execute after the adjournment phase (if applicable) or immediately after the trigger (for non-meeting sessions).

### Step 0: Confirm Intent

Before executing any write actions, confirm intent: **"Wrapping up the session. I'll update the task list and write the experience log."**

This gives the user a chance to say "wait, one more thing" before irreversible actions begin. If the user continues discussing, defer close and return to active discussion. Re-invoke the close protocol when the user signals end again.

### Step 1: Update `tasks.md`

Read the current `tasks.md` from `<project_root>/` (or create it if it doesn't exist). Update it to reflect:

- Tasks completed during this session — mark as done.
- New tasks identified during discussion — add to the list.
- Tasks deferred or deprioritized — annotate with reason.

Write the updated file.

Format: simple markdown checklist.

```md
# Tasks — <project-name>

- [x] Completed task (completed YYYY-MM-DD)
- [ ] Pending task
- [ ] New task from this session
```

**Failure handling:**

- File write fails — **warn user**. Print the task list to the terminal so the user can save it manually.

### Step 1.3: Check for Unreviewed Subagent Outputs

Scan the `subagent-outputs/` directory for any files that were **not** reviewed during this session. A subagent output counts as "reviewed" if it was reintegrated via the Reintegration Protocol (Section 6 of the subagent-delegation protocol) during the current session. Any remaining files are unreviewed — typically from background delegations that completed after the discussion moved on, or outputs that arrived near session end.

For each unreviewed output file:

1. Read only the frontmatter (`status` field) and the first line of the Executive Summary.
2. Add a task to `tasks.md` with the format:

```md
- [ ] Review subagent output: `subagent-outputs/<filename>` (status: <status>)
```

3. If the `status` is `failed` or `partial`, note this in the task so it gets appropriate attention.

After processing, report to the user: **"Found N unreviewed subagent output(s). Added review tasks to tasks.md."** If there are no unreviewed outputs, skip this step silently.

**Failure handling:**

- `subagent-outputs/` directory does not exist or is empty — skip silently.
- A file cannot be read — add the task anyway with status `unknown`, and warn the user.

### Step 1.5: Write Session History

Write a session history file to `sessions/YYYY-MM-DD-NNN.md` (where `NNN` is a zero-padded sequence number for the day, e.g., `001`). The session history captures the factual record of what happened during this session.

The session history file must include:

- **Date and session identifier** — the filename-derived date and sequence number.
- **Agenda items addressed** — what topics were discussed, in order.
- **Decisions made** — each decision with its rationale and any dissenting considerations.
- **Artifacts produced** — files created or modified, with brief descriptions.
- **Open questions** — anything raised but not resolved during the session.
- **Subagent Dispatches** *(optional)* — included when subagents were delegated during the session; omitted when no delegation occurred. See [Subagent Dispatches Schema](#subagent-dispatches-schema) below.
- **Pipeline State** *(optional, Phase 5)* — included when Phase 5 pipeline features are active for the project. See [Pipeline State Schema](#pipeline-state-schema) below.

Format:

```md
# Session History — YYYY-MM-DD-NNN

## Agenda

- Topic 1
- Topic 2

## Decisions

- **Decision:** <what was decided>
  **Rationale:** <why>

## Artifacts

- `path/to/file` — description of what was created or changed.

## Open Questions

- Question or unresolved item.

## Subagent Dispatches

| Task | Skill | Depth | Status | Output |
|------|-------|-------|--------|--------|
| <task description> | <skill or "ad-hoc"> | light/deep | completed/partial/failed | `subagent-outputs/<filename>.md` |

### <Task description>

- **Delegated:** <what was asked and why — one sentence>
- **Result:** <what came back — outcome summary, not full content>
- **Follow-up:** <what was done with the result — incorporated, deferred, re-delegated>

## Pipeline State

- **Discovery queue:** <N papers pending review / empty / not configured>
- **Living review:** <last run date, or "not configured">
- **Checkpoints:** <N unreviewed / all reviewed / none pending>
- **Health digest:** <last digest date, current status, or "not configured">
```

The "Subagent Dispatches" section has two parts: a **dispatch table** for quick scanning, and **per-task narrative entries** for context. Both are written from the main agent's perspective (what was delegated and what came back), not from the subagent's perspective. The subagent's full account is in the output file referenced in the table's Output column. This bidirectional reference — session history pointing to the output file, and the output file's `requested_by`/`date` frontmatter pointing back — connects the session record to the subagent's detailed output.

#### Subagent Dispatches Schema

The "Subagent Dispatches" section is an **optional** section of the session history, included whenever subagents were used during the session and omitted when no delegation occurred.

**Dispatch table** — one row per delegated task:

| Column | Description |
|--------|-------------|
| **Task** | Brief description of the delegated task |
| **Skill** | The skill used (e.g., `paper-reader`, `paper-discovery`, `knowledge-maester`, `visual-architect`) or `ad-hoc` for tasks not matching a named skill |
| **Depth** | `light` or `deep` (per Section 2 of the subagent-delegation protocol) |
| **Status** | Final status: `completed`, `partial`, or `failed` (from the subagent output's frontmatter) |
| **Output** | Path to the subagent output file, e.g., `subagent-outputs/YYYY-MM-DD-<slug>.md` |

**Per-task narrative** — one subsection per delegated task (heading matches the Task column entry):

| Field | Description |
|-------|-------------|
| **Delegated** | What was asked and why — a single sentence capturing the objective and motivation |
| **Result** | What came back — outcome summary, not full content (the detail lives in the output file) |
| **Follow-up** | What was done with the result: incorporated into the discussion, deferred to a future session, re-delegated with a revised brief, etc. |

The table provides a quick scan; the per-task narratives provide context. Together they form the session-level audit trail for subagent usage. The dispatch table is a summary, not a log — it records what was delegated and what came back, following the "index, not encyclopedia" principle.

#### Pipeline State Schema

The "Pipeline State" section is an **optional** section of the session history, included when Phase 5 pipeline features (living review, health digest, discovery queue) are active for the project. It is omitted when no Phase 5 pipeline features are configured.

This section captures a snapshot of the pipeline's state at session close, providing continuity between sessions. The next session's startup (Steps 5a-5c) reads this state to present relevant alerts.

| Field | Description |
|-------|-------------|
| **Discovery queue** | Number of papers pending review, or "empty", or "not configured" |
| **Living review** | Date of the last living review run, or "not configured" |
| **Checkpoints** | Count of unreviewed pipeline checkpoints, or "all reviewed", or "none pending" |
| **Health digest** | Date of the last health digest and its status (green/yellow/red), or "not configured" |

**How to populate:** Read the current state from the project's `pipeline/` directory. Each field corresponds to a file or directory checked during startup Steps 5a-5c. If a pipeline component's directory does not exist, record "not configured" for that field.

**Failure handling:**

- `pipeline/` directory does not exist — omit the entire Pipeline State section silently.
- Individual pipeline component unreadable — record "unknown" for that field and continue.

### Step 1.7: Update Project Summary

Update the project summary at `memory/latest-summary.md` using anchored iterative extension. This means:

1. Read the existing `memory/latest-summary.md` (if it exists).
2. Identify which sections are affected by this session's work.
3. Extend or revise only the affected sections — do not rewrite sections that have not changed.
4. If the file does not exist, create it with a complete project summary based on available context.

The project summary should reflect the cumulative state of the project, not just this session. It serves as a quick-reference document for future sessions to understand where the project stands.

Recommended sections:

- **Project goal** — one-line description of the project's objective.
- **Current status** — what phase or milestone the project is in.
- **Key decisions** — important decisions that shape the project direction.
- **Active work streams** — what is currently in progress.
- **Known blockers or risks** — anything impeding progress.

**Failure handling:**

- File write fails — **warn user**. Print the summary update to the terminal so the user can save it manually.

### Step 2: Remind About Session-Handoff

If the session involved significant decisions, design changes, or context that a future agent would need, remind the user: "This session had substantive decisions. Consider writing a handoff — invoke the `session-handoff` skill when ready."

The close protocol does NOT auto-invoke `session-handoff`. The user decides when and whether to write a handoff.

### Step 3: Run Experience-Logger

Invoke the `experience-logger` skill for the active project. The experience log must include:

- Standard experience-logger sections (task objective, actions taken, outputs produced, corrections, lessons).
- `## Workflow Reflection` — how this session followed or deviated from the workflow template.
- `## Research Meeting Session Observations` — raw observations about the session pattern (startup, discussion flow, decisions, close) as material for future workflow refinement.

**Failure handling:**

- `experience-logger` skill unavailable — **warn user**. The session can close without it, but warn: "Experience logger is not available. No experience log was written. Session decisions are only in tasks.md and chat history."

### Step 3.3: Digest Update Consideration (Conditional)

*Phase 5 (P5-D5) — conditional step. Skipped if no Phase 5 features are configured or if the session did not involve significant work.*

After the experience log is written, evaluate whether the session's work warrants a health digest update. A digest update is warranted when:

- New findings were added to `findings.md` or the shared workspace.
- Pipeline state changed materially (new papers screened, checkpoints reviewed, data processed).
- Key project decisions were made that shift risk profile or project direction.
- A prior digest's alert was addressed or a new risk was identified.

If any of these conditions are met, suggest to the user: **"This session involved significant work that may affect the project's health profile. Consider running a health digest update — invoke the `health-digest` skill when ready."**

If none of these conditions are met, skip this step silently.

The close protocol does **NOT** auto-invoke the health digest. The user decides whether and when to run it. This step is a suggestion only.

**Failure handling:**

- Cannot determine whether work was significant (e.g., workspace unreadable) — skip silently. A missed suggestion is preferable to a false positive.

### Step 3.5: Central Memory Promotion Reminder (Conditional)

This step is **conditional** — it is only executed when the session produced insights, patterns, or corrections that have cross-session value and are not already captured in the project's central memory files.

If the condition is met, remind the user: "This session produced learnings that may be worth promoting to central memory. Review the experience log and consider updating memory files (e.g., feedback, project context, or reference pointers)."

The close protocol does **NOT** auto-invoke memory promotion. The user decides whether and what to promote. This step is a reminder only.

**When to trigger:**

- A workflow correction was discovered that would prevent future mistakes.
- A new external reference or resource was identified.
- A project-level decision was made that changes the project's direction or constraints.
- The user explicitly asked the agent to "remember" something during the session.

**When to skip:**

- The session was routine with no novel learnings.
- All relevant context is already captured in existing memory files.

### Step 3.7: Glossary Maintenance (Optional)

*Phase 5 (P5-D5) — optional step. Skipped if voice mode was not used during the session or if no Phase 5 voice features are configured.*

If voice mode (`/voice`) was active during the session, check whether any transcription errors were corrected by the user or detected by the agent. If corrections occurred, offer to update the project's domain glossary:

**"Voice mode was active this session and I noticed transcription corrections. Would you like me to update `voice-glossary.yaml` with the new entries?"**

If the user agrees, update `<project_root>/voice-glossary.yaml`:

1. Read the existing glossary (or create it from the starter template at `templates/voice-glossary.yaml` if it does not exist).
2. For each new correction observed during the session:
   - If the correct term already exists in the glossary, add the new mistranscription to its `mistranscriptions` list (avoid duplicates).
   - If the correct term is new, add a new entry with the appropriate category (`terms`, `authors`, or `notation`).
3. Update the `last_updated` field to today's date.
4. Write the updated file.

If no transcription corrections were observed, skip this step silently. Do not prompt the user about glossary maintenance when there is nothing to add.

**When to trigger:**

- Voice mode was active AND at least one transcription correction was made (user typed a correction, or the agent flagged and corrected a domain term).

**When to skip:**

- Voice mode was not used during the session.
- Voice mode was used but no transcription errors were observed or corrected.
- The project does not have Tier 2 voice correction configured (no glossary file and user has not opted into voice correction).

**Failure handling:**

- Glossary file write fails — **warn user**. Print the new entries to the terminal so the user can add them manually.
- Starter template not found — create a minimal glossary with just the new entries and the standard schema header.

### Step 4: Final Summary

Print a brief summary of what was accomplished:

- Decisions made.
- Tasks completed.
- Tasks added.
- Files modified or created.
- **Pipeline state** *(Phase 5, if active)* — current state of discovery queue, living review, checkpoints, and health digest. This mirrors the Pipeline State section written to the session history in Step 1.5, giving the user a verbal summary before session end.

This is the last output of the session.

---

## Edge Cases

### E1: User closes abruptly ("gotta go, bye")

Execute a minimal close: Step 1 (update `tasks.md`) only. Steps 2–4 are skipped. Phase 5 steps (3.3, 3.7) are also skipped. If even Step 1 can't complete, the session ends without persistence — this is an accepted loss.

### E2: Nothing happened in the session

If no decisions were made and no tasks changed, skip Steps 1–3 and report: "No changes to persist. Session complete." Phase 5 steps (3.3, 3.7) are also skipped — no work means no digest consideration and no glossary updates.

### E3: Session was interrupted (context limit, crash)

The agent cannot execute the close protocol if the session is interrupted externally. This is unrecoverable by design. The handoff from the previous session remains the latest state. The next session detects that no new handoff was written and proceeds accordingly.

Mitigation: use the context-checkpoint protocol proactively during long sessions to persist progress incrementally, so that an interruption loses at most the work since the last checkpoint.

### E4: User asks to close but then continues discussing

After the agent announces the close (Step 0 confirmation), the user may add more items. The agent defers close and returns to active discussion. The close protocol is re-invoked when the user signals end again.
