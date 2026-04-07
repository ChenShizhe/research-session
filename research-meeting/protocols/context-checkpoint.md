# Context Checkpoint Protocol

## Purpose

Persist mid-session progress to durable files so that: (a) the persisted context can be evicted from the active context window, freeing space for further discussion; and (b) if the session is interrupted (crash, context limit, autocompact), the work since the last checkpoint is not lost.

## Trigger

The user explicitly asks to persist progress. Examples:

- "Write down what we've discussed so far."
- "Checkpoint this — I want to free up context."
- "Save our decisions before we continue."

The agent may also suggest a checkpoint when context usage is high, but does not auto-invoke without user confirmation.

---

## Steps

### Step 1: Identify what to persist

Review the session's discussion since the last checkpoint (or since session start, if no checkpoint has been taken). Identify:

- Decisions made.
- Design outcomes or conclusions.
- Task status changes.
- Any structured content that was produced in discussion but not yet written to files.

If nothing substantive has changed since the last checkpoint, report that and skip Steps 2–3.

### Step 2: Write to appropriate files

Persist each category to its natural location:

- Decisions and design outcomes — update `handoff.md` (append to Key Decisions section) or write to relevant design/notes files.
- Task changes — update `tasks.md`.
- Structured content (draft specs, analysis results) — write to project files (e.g., `designs/`, `notes/`, or wherever the content belongs).

The checkpoint does NOT create new file types. It writes to existing project files, keeping the file structure clean.

### Step 3: Report what was persisted

Tell the user what was written and where. Example: "Checkpointed: 3 decisions added to handoff.md, tasks.md updated with 2 new items, draft analysis written to notes/simulation-plan.md."

This report also serves as a marker — the agent and user both know that everything before this point is safely persisted and eligible for context eviction.

---

## Design Notes

### Lightweight by design

The checkpoint protocol is a pure write operation. It does not invoke `experience-logger`, `memory-retriever`, or any other skill. This keeps it fast and avoids consuming context budget on tool orchestration.

### Incremental and repeatable

Multiple checkpoints per session are fine. Each checkpoint is incremental — it only persists content that is new since the last checkpoint (or since session start). The close protocol handles final persistence; if the user checkpointed recently, the close protocol has less to do.

### Distinction from session-handoff

A checkpoint updates individual project files incrementally (tasks.md, handoff.md, design docs). A session-handoff produces a complete cross-session continuity document designed to bootstrap the next session from scratch. Both can happen in the same session — they serve different purposes.

### Distinction from the close protocol

The close protocol runs once at session end and performs a comprehensive wrap-up: updating tasks.md, reminding about session-handoff, invoking experience-logger, and printing a final summary. The checkpoint protocol can run multiple times mid-session and only persists what has changed. The close protocol assumes any prior checkpoints have already been written and focuses on final-state persistence and session teardown.

---

## Edge Cases

### E1: Nothing to checkpoint

If no decisions, task changes, or structured content have been produced since the last checkpoint, report: "Nothing new to checkpoint since the last save." Skip Steps 2–3.

### E2: User asks to checkpoint immediately after session start

Likely nothing to persist. Same as E1. Report accordingly.

### E3: Checkpoint requested during close

If the user asks for a checkpoint after the close protocol has been announced, defer to the close protocol — it will handle all remaining persistence. Inform the user: "The close protocol will persist everything. No separate checkpoint needed."
