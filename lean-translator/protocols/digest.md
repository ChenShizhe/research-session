# Protocol: `digest`

## Purpose

Produce a structured rollup of Lean translation status for surfacing in two contexts:

1. **Mid-session pull** — when the user asks "how's the Lean translation going?" or similar, the agent runs `digest` and prints the result in chat.
2. **Session-start push** — when a session-handoff document contains a `## Lean status` section, that section is populated by `digest` at handoff-write time.

`digest` is the failure-surfacing mechanism. Per the proposal-15 design decision, failures are **not** surfaced at session close; they surface either when the user asks (pull) or at the start of the next session via the handoff (push). `digest` powers both surfaces.

## Invocation cues

- "how's the lean translation going?"
- "lean status?"
- "any new lean failures?"
- "show me the pending-review queue"
- Implicit, during `session-handoff` write: the handoff skill calls this protocol if the project has a Lean project.

## Prerequisites

- `<vault_root>/theory/lean/` exists
- `_attempts/` directory exists (created by scaffold)

## Steps

### 1. Aggregate vault frontmatter status

Walk every vault node. Tally `lean_status` by value. Identify:

- `pending-review-queue`: list of nodes with `lean_status: verified-pending-review` (the human-gate backlog)
- `local-axioms-queue`: list of nodes with `lean_status: verified-local-axioms` (also need parity-review, with the local-axioms qualifier)
- `recent-failures`: list of nodes with `lean_status: failed` and `lean_attempted_at` within the last 7 days (configurable)
- `stale-queue`: list of nodes with `lean_status: stale`

### 2. Aggregate diagnostics from `_attempts/`

Walk `<vault_root>/theory/lean/_attempts/*.lean-attempt.md`. For each, read frontmatter `diagnostics_class`. Group recent (last-7-day) failures by class:

- `translation-bug`: count + node list
- `dep-mismatch`: count + node list
- `proof-gap`: count + node list

### 3. Format the digest

Markdown structure. Order: queue first (action items), then failures (information), then summary line.

```markdown
## Lean status

**Pending-review queue** (statement-parity human gate required):
  - <node-id> (<status: verified-pending-review | verified-local-axioms>)
  - ...

**Recent failures** (last 7 days):
  - translation-bug: <N>
    - <node-id>, <node-id>, ...
  - dep-mismatch: <N>
    - <node-id>, <node-id>, ...
  - proof-gap: <N>
    - <node-id>, <node-id>, ...

**Stale (vault edited since last translation)**: <count> nodes — re-translation queued

**Summary**: `lean: nodes=N verified=V failed=F stale=S not-attempted=A pending-review=R`
```

### 4. Surface mode

**Mid-session pull (chat output):** Print the digest directly in chat. Cap the per-section list at 10 entries; if more, append `... and <K> more (see <vault>/theory/lean/_meta/ for full list)`.

**Session-start push (handoff section):** Use the template at `~/Documents/skills/research-session/lean-translator/templates/handoff-lean-section.md.template` and substitute. The `session-handoff` skill picks up the resulting markdown and includes it as a section in the handoff document.

### 5. Empty digests

If the digest is empty (no pending-review, no recent failures, no stale), suppress the section entirely on session-start push (do not emit an empty `## Lean status` section in handoffs). On mid-session pull, emit a one-line acknowledgment: `lean status: all caught up (verified=V, not-attempted=A, no pending review, no recent failures)`.

## What `digest` does NOT do

- Does not modify vault frontmatter.
- Does not run `lake build`.
- Does not dispatch translator subagents.
- Does not delete failed-attempt files (those are kept indefinitely for audit).
- Does not surface at session-close (explicit user constraint — see proposal 15).
