# Workspace FORMAT Reference

> Canonical specification for the shared workspace used during research-meeting sessions.
> This protocol is **identical across all runtime tiers** (Tier 1 / Tier 2 / Tier 3).

---

## 1. Directory Structure

```
workspace/
├── agenda.md                # Session agenda and topic ordering
├── transcript.md            # Running transcript of the discussion
├── findings.md              # Consolidated findings accepted by the group
├── questions.md             # Open questions surfaced during the session
├── FORMAT.md                # Copy of this specification (self-describing)
├── contributions/           # One file per contribution from any specialist
│   └── {seq}-{agent}-{type}.md
├── inboxes/                 # Per-specialist JSONL message queues
│   └── {agent-id}.jsonl
├── specialist-state/        # Per-specialist crash-recovery summaries
│   └── {agent-id}.md
└── artifacts/               # Produced artifacts (diagrams, code, data, etc.)
    └── {descriptive-name}.{ext}
```

## 2. File Purposes and Ownership

| File / Directory | Purpose | Owner (sole writer) |
|---|---|---|
| `agenda.md` | Ordered list of topics, time-boxes, and goals for the session. | Group Lead |
| `transcript.md` | Append-only log of accepted contributions in discussion order. | **Group Lead** |
| `findings.md` | Curated, group-endorsed findings distilled from the discussion. | **Group Lead** |
| `questions.md` | Running list of open questions; any specialist may append. | Any Specialist (append-only) |
| `FORMAT.md` | This specification, copied into the workspace at session start. | System (read-only at runtime) |
| `contributions/` | Individual contribution files; one file per contribution. | Authoring Specialist (own files only) |
| `inboxes/` | Per-specialist JSONL message queues for peer-to-peer messaging. | Any agent may **append** to another specialist's inbox file. |
| `specialist-state/` | Crash-recovery state summaries. Each specialist writes only its own file. | Authoring Specialist (own file only) |
| `artifacts/` | Session artifacts (figures, code, datasets). | Authoring Specialist (own files only) |

---

## 3. Contribution Format

Each contribution is a single Markdown file in `contributions/` with YAML frontmatter followed by a Markdown body.

### 3.1 File Naming

```
{seq}-{agent-id}-{type}.md
```

- **seq**: Zero-padded 4-digit sequence number (e.g., `0001`, `0042`).
- **agent-id**: The contributing specialist's identifier (e.g., `methodologist`, `domain-expert`).
- **type**: One of the six contribution types listed below.

Example: `0007-methodologist-finding.md`

### 3.2 YAML Frontmatter Schema

```yaml
---
seq: 7                        # Integer sequence number assigned by the contributor
agent: "methodologist"        # Specialist identifier (string)
type: "finding"               # Contribution type (see §3.3)
confidence: "high"            # Confidence level (see §3.4)
in-reply-to: 4                # Optional: seq number of the contribution this responds to
references: [2, 5]            # Optional: list of seq numbers referenced
tags: ["sampling", "bias"]    # Optional: free-form topic tags
timestamp: "2026-04-03T14:22:07Z"  # ISO-8601 UTC timestamp
---
```

**Required fields:** `seq`, `agent`, `type`, `confidence`, `timestamp`
**Optional fields:** `in-reply-to`, `references`, `tags`

### 3.3 Contribution Types

| Type | Purpose |
|---|---|
| `finding` | A substantive claim, result, or conclusion the specialist wants the group to consider. |
| `question` | A question directed at the group or a specific specialist. |
| `challenge` | A disagreement, counter-argument, or identified flaw in a prior contribution. |
| `suggestion` | A proposed direction, method, or action for the group to consider. |
| `response` | A direct reply to a prior `question`, `challenge`, or `request-to-speak`. |
| `request-to-speak` | A signal that the specialist wants the floor to present extended reasoning. |

### 3.4 Confidence Levels

| Level | Meaning |
|---|---|
| `high` | Strong evidence or well-established reasoning supports the contribution. |
| `medium` | Reasonable support exists but some uncertainty remains. |
| `low` | Preliminary or speculative; limited evidence or untested reasoning. |
| `uncertain` | The contributor is flagging an open issue with no clear assessment of likelihood. |

### 3.5 Markdown Body

The body after the frontmatter closing `---` is free-form Markdown. It should contain the substance of the contribution. There is no enforced body schema, but contributors are encouraged to be concise and cite evidence where possible.

---

## 4. Sequence Numbering and Collision Handling

### 4.1 Assignment

Each specialist maintains a local counter. Before writing a contribution, the specialist scans `contributions/` for the current maximum sequence number and assigns `max + 1`.

### 4.2 Collision Handling

Because multiple specialists may race to claim the same sequence number:

1. **Detect**: Before writing, check whether a file with the target `{seq}-*` prefix already exists.
2. **Increment**: If a collision is detected, increment the sequence number and re-check until an unused number is found.
3. **Atomicity**: Write the contribution file in a single operation (write-to-temp then rename) to prevent partial reads.
4. **Idempotency**: If a specialist crashes after writing but before confirming, it may re-scan and find its own file. The `agent` and `timestamp` fields in frontmatter serve as deduplication keys.

> **Invariant**: No two contribution files may share the same sequence number. The filename is the source of truth for ordering.

---

## 5. Read/Write Protocol

### 5.1 Core Rules

1. **Group Lead is the sole writer** to `transcript.md` and `findings.md`. No specialist may write to these files directly.
2. **Specialists write only to their own files**: each specialist writes to its own contribution files in `contributions/`, its own state file in `specialist-state/`, and its own artifact files in `artifacts/`.
3. **One-file-per-contribution concurrency**: Because each contribution is a separate file with a unique name, multiple specialists can write contributions simultaneously without file-level conflicts.
4. **Append-only inboxes**: Any agent may append a line to any specialist's inbox JSONL file. Readers tolerate concurrent appends via line-based parsing.
5. **`questions.md` is append-only**: Any specialist may append to `questions.md`. Appends must be atomic (write full line/block in one operation).

### 5.2 Read Permissions

All files in the workspace are **readable by all agents**. There are no read restrictions.

### 5.3 Write Permission Matrix

| Target | Group Lead | Specialists | System |
|---|---|---|---|
| `agenda.md` | write | read-only | read-only |
| `transcript.md` | **write (sole)** | read-only | read-only |
| `findings.md` | **write (sole)** | read-only | read-only |
| `questions.md` | append | append | read-only |
| `FORMAT.md` | read-only | read-only | write (init only) |
| `contributions/{own}` | — | write (own files) | — |
| `inboxes/{any}.jsonl` | append | append | — |
| `specialist-state/{own}` | — | write (own file) | — |
| `artifacts/{own}` | — | write (own files) | — |

### 5.4 Concurrency Safety Summary

- No two agents ever write to the same file (except append-only targets: `inboxes/*.jsonl` and `questions.md`).
- Append-only targets use line-based (JSONL) or block-based (Markdown) atomic appends so concurrent writers do not corrupt each other's data.

---

## 6. Inbox JSONL Format

Each specialist has an inbox file at `inboxes/{agent-id}.jsonl`. Messages are one JSON object per line (JSONL / JSON Lines format).

### 6.1 Message Schema

```json
{
  "from": "domain-expert",
  "to": "methodologist",
  "type": "direct",
  "ref": 12,
  "subject": "Clarification on sampling approach",
  "body": "Could you elaborate on why stratified sampling is preferred here?",
  "timestamp": "2026-04-03T14:30:00Z"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `from` | string | yes | Sender agent identifier. |
| `to` | string | yes | Recipient agent identifier (must match the inbox filename). |
| `type` | string | yes | Message type: `"direct"` (peer message), `"system"` (system notification), `"nudge"` (gentle prompt to contribute). |
| `ref` | integer | no | Contribution sequence number this message relates to. |
| `subject` | string | no | Short subject line for the message. |
| `body` | string | yes | Message content (plain text or inline Markdown). |
| `timestamp` | string | yes | ISO-8601 UTC timestamp. |

### 6.2 Protocol Rules

- Writers **append** one JSON line at a time. Never rewrite or truncate another agent's inbox file.
- Readers parse line-by-line and tolerate a trailing incomplete line (from a concurrent write) by skipping it.
- Agents should poll their own inbox file periodically and track the last-read byte offset or line count to avoid reprocessing.
- Inbox files are **not** garbage-collected during a session; they serve as an audit trail.

---

## 7. Specialist State Summary Format (Crash Recovery)

Each specialist maintains a state summary at `specialist-state/{agent-id}.md` for crash recovery. If a specialist is restarted mid-session, it reads this file to restore context.

### 7.1 Required Sections

```markdown
# Specialist State: {agent-id}

## Current Understanding
<!-- What the specialist currently believes about the topic under discussion. -->

- Key point 1 derived from contributions and discussion so far.
- Key point 2...

## Active Reasoning
<!-- What the specialist is currently working on or thinking through. -->

- Current line of analysis or argument being developed.
- Hypotheses being evaluated.

## Open Items
<!-- Unresolved questions, pending tasks, or follow-ups the specialist is tracking. -->

- Open question or pending action 1.
- Open question or pending action 2.
```

### 7.2 Field Descriptions

| Section | Purpose |
|---|---|
| **Current Understanding** | A concise summary of the specialist's accumulated understanding of the discussion topic. Enables a restarted agent to resume without re-reading all contributions. |
| **Active Reasoning** | Captures in-progress analysis, partially formed arguments, or hypotheses the specialist was evaluating at time of last checkpoint. |
| **Open Items** | Tracks unresolved questions the specialist has posed or received, pending responses, and any self-assigned follow-up tasks. |

### 7.3 Update Frequency

- Specialists **must** update their state file after submitting each contribution.
- Specialists **should** update their state file after reading new contributions from others that materially change their understanding.
- The state file is **overwritten** (not appended) on each update — it represents a point-in-time snapshot.

---

## 8. Group Lead Integration Workflow

The group lead is responsible for integrating specialist contributions into a coherent discussion. This section defines the integration cycle, round limits, and decision protocols.

### 8.1 Integration Cycle

For each topic on the agenda, the group lead follows a four-phase integration cycle:

1. **Read** — The group lead reads all new contributions in `contributions/` since the last integration pass, noting each contribution's type, confidence level, and relationship to prior contributions (via `in-reply-to` and `references` fields).

2. **Evaluate** — The group lead assesses the contributions for:
   - **Relevance**: Does the contribution address the current agenda topic?
   - **Novelty**: Does it introduce new information, or restate what is already captured?
   - **Consistency**: Does it agree with, refine, or contradict existing findings?
   - **Confidence**: Are high-confidence findings corroborated? Are low-confidence claims flagged for further discussion?

3. **Transcribe** — The group lead appends accepted contributions to `transcript.md` in discussion order, preserving attribution (specialist identifier and sequence number). Contributions that are off-topic, redundant, or superseded may be omitted from the transcript with a brief note explaining the omission.

4. **Synthesize** — The group lead distills the transcribed contributions into updated entries in `findings.md`. Synthesis includes:
   - Merging compatible findings into consolidated statements.
   - Noting unresolved disagreements or open questions (cross-referencing `questions.md`).
   - Updating confidence assessments based on corroboration or challenge from multiple specialists.

After synthesis, the group lead may broadcast a summary or follow-up prompt to specialist inboxes to guide the next round of contributions.

### 8.2 Round Limits per Topic

Each agenda topic proceeds through discussion rounds. A **round** is one full cycle of specialist contributions followed by a group lead integration pass.

- **Soft limit: 2–3 rounds per topic.** Most topics should converge within 2–3 rounds of discussion. This is a planning guideline, not a hard cutoff — the group lead may extend discussion if meaningful progress is still being made or if a critical disagreement remains unresolved.
- **When to extend beyond 3 rounds:** The group lead should continue only when (a) new substantive evidence is being introduced, (b) a safety-critical or high-stakes disagreement has not been adequately addressed, or (c) a specialist has explicitly requested the floor via `request-to-speak` and has not yet been heard.
- **When to close early:** If consensus is reached in fewer than 2 rounds, the group lead should close the topic and move on rather than soliciting unnecessary additional rounds.

### 8.3 Decision Protocol

When a topic requires a group decision (e.g., accepting a finding, choosing between competing interpretations), the group lead applies one of two protocols depending on the nature of the decision:

| Decision Type | Protocol | When to Use |
|---|---|---|
| **Reasoning / interpretive** | Voting | The question involves judgment, interpretation, or weighing competing arguments where reasonable specialists may disagree. |
| **Factual / empirical** | Consensus | The question has a determinable correct answer grounded in evidence, data, or established methodology. |

#### Voting (for reasoning tasks)

1. The group lead poses the decision as a clear question to all specialists (via inbox broadcast or a dedicated prompt in the transcript).
2. Each specialist submits a `response` contribution stating their position and reasoning.
3. The group lead tallies positions and records the outcome in `findings.md`, including the majority position, any dissenting views, and the reasoning behind each.
4. Minority positions are preserved in the findings — voting resolves the group's forward direction, not the correctness of dissenting views.

#### Consensus (for factual tasks)

1. The group lead identifies the factual claim and the evidence cited by each specialist.
2. If all specialists agree (or none have challenged the claim), the group lead records the finding as accepted.
3. If a specialist challenges the factual basis, the group lead requests supporting evidence from the relevant parties. Discussion continues until the evidence resolves the disagreement or the group lead determines the claim should be recorded as uncertain.
4. Consensus does not require unanimity on interpretation — it requires agreement on the underlying facts. Interpretive disagreements that surface during a factual consensus check are escalated to a voting decision.

### 8.4 Integration Pass Timing

The group lead performs an integration pass:

- After each round of specialist contributions (i.e., when activity in `contributions/` has paused or all expected specialists have contributed).
- Before transitioning to a new agenda topic.
- Before initiating a decision protocol (to ensure the latest contributions are reflected in findings).

---

## 9. Cross-Tier Compatibility

This workspace protocol is **identical across all runtime tiers** (Tier 1 / Tier 2 / Tier 3). Implementations must not introduce tier-specific file formats, naming conventions, or protocol deviations. Any agent, regardless of its runtime tier, must be able to read and write workspace files using the formats specified in this document.

---

## 10. Session History Extension: Multi-Agent Contributions

When a session uses multi-agent mode, the session history file (written during session close at `sessions/YYYY-MM-DD-NNN.md`) must include a **Multi-Agent Contributions** section. This section is **conditional** — it is included only when `multi_agent_mode: true` was set during session startup, and omitted for single-agent sessions.

The Multi-Agent Contributions section sits after the standard session history sections (Agenda, Decisions, Artifacts, Open Questions) and before or after the Subagent Dispatches section (if present). It captures **who participated as specialists** and **how specialists interacted with each other** during the session.

### 10.1 Section Format

```md
## Multi-Agent Contributions

### Participants

| Specialist | Role | Contributions | Key Topics |
|------------|------|---------------|------------|
| <agent-id> | <role description> | <count> | <comma-separated topic list> |

### Cross-Specialist Interactions

- **<interaction-type>:** <agent-A> → <agent-B> — <one-sentence description of the interaction and its outcome>
```

### 10.2 Participants Table

The participants table lists every specialist that was active during the session. One row per specialist.

| Column | Description |
|--------|-------------|
| **Specialist** | The specialist's agent identifier (e.g., `methodologist`, `domain-expert`). Must match the `agent` field used in contribution frontmatter. |
| **Role** | A brief description of the specialist's role in this session (e.g., "Statistical methodology advisor", "Domain expert on protein folding"). |
| **Contributions** | The total number of contributions the specialist submitted (count of files in `contributions/` authored by this agent). |
| **Key Topics** | Comma-separated list of the primary topics the specialist addressed, derived from the specialist's contribution `tags` fields and the agenda items they engaged with. |

The group lead is **not** listed in the participants table — it is the author of the session history and its role is implicit. Only recruited specialists appear.

### 10.3 Cross-Specialist Interactions

This subsection records the most significant interactions between specialists during the session. Each entry is a single bullet describing one interaction. The group lead selects interactions that materially shaped the session's findings or decisions.

Each interaction entry follows this format:

```
- **<interaction-type>:** <agent-A> → <agent-B> — <description>
```

**Interaction types:**

| Type | When to use |
|------|-------------|
| `Challenge` | One specialist challenged another's finding, claim, or methodology. |
| `Corroboration` | One specialist provided independent evidence or reasoning supporting another's contribution. |
| `Synthesis` | Two or more specialists combined their contributions into a joint finding or refined conclusion. |
| `Delegation` | One specialist deferred a question or sub-problem to another specialist with relevant expertise. |
| `Clarification` | One specialist requested and received clarification from another, resolving an ambiguity. |

**Selection criteria:** The group lead includes interactions that:

1. Led to a change in the session's findings or decisions.
2. Resolved a disagreement or open question.
3. Combined perspectives from different specialties into a stronger result.

Routine exchanges (e.g., acknowledgments, minor clarifications that did not affect outcomes) are omitted. Aim for 3–8 interaction entries per session — enough to capture the collaborative dynamics without exhaustive logging.

### 10.4 Example

```md
## Multi-Agent Contributions

### Participants

| Specialist | Role | Contributions | Key Topics |
|------------|------|---------------|------------|
| methodologist | Statistical methodology advisor | 5 | sampling, bias correction, power analysis |
| domain-expert | Protein folding domain specialist | 4 | structural prediction, AlphaFold limitations |
| literature-reviewer | Systematic review specialist | 3 | prior work, meta-analysis coverage |

### Cross-Specialist Interactions

- **Challenge:** methodologist → domain-expert — Questioned the sample size assumptions in the proposed validation experiment; led to a revised power analysis accepted as Finding #7.
- **Corroboration:** literature-reviewer → methodologist — Cited three prior studies confirming the bias correction approach, strengthening confidence in Finding #3 from medium to high.
- **Synthesis:** domain-expert + methodologist — Combined structural prediction constraints with statistical feasibility analysis to produce the final experimental design (Finding #12).
- **Clarification:** domain-expert → literature-reviewer — Clarified that AlphaFold v2.3 results are not directly comparable to earlier versions, correcting a citation scope issue in the literature review.
```

### 10.5 Relationship to Other Session History Sections

The Multi-Agent Contributions section complements but does not replace existing session history sections:

- **Decisions** records *what* was decided. Multi-Agent Contributions records *who contributed to* those decisions and *how specialists influenced each other*.
- **Subagent Dispatches** records delegations to subagents (skill-based workers). Multi-Agent Contributions records interactions between *peer specialists* participating in the live discussion.
- **Artifacts** records files produced. The participants table's Contributions column counts discussion contributions (files in `contributions/`), not artifacts.

---

## 11. Single-Agent Fallback

When multi-agent mode is not used, the session operates as a standard single-agent session with no degraded experience. This section defines the two scenarios that trigger single-agent fallback and the resulting behavior.

### 11.1 Trigger Scenarios

Single-agent fallback activates in exactly two situations:

| Scenario | Trigger Point | What Happens |
|---|---|---|
| **User declines specialists** | Step 5 of the session startup protocol. The group lead asks whether the session should use multi-agent mode, and the user says no (or does not respond affirmatively). | The group lead sets `multi_agent_mode: false` and skips Steps 6–10 entirely. The session proceeds directly to Step 11 (Transition to Active Discussion). |
| **All specialists fail** | Steps 6–9 of the session startup protocol. Specialists cannot be spawned (Step 8 failure), no specialists pass the readiness barrier (Step 9 timeout), or no tasks are suitable for parallel work (Step 6 assessment). | The group lead sets `multi_agent_mode: false`, reports the failure to the user, and proceeds to Step 11 (Transition to Active Discussion). |

In both cases the outcome is the same: the session reverts to standard single-agent operation.

### 11.2 Fallback Behavior

When single-agent fallback is active, the session operates under these rules:

1. **The group lead handles all work directly.** There are no specialists, no roster, and no workspace directories specific to multi-agent coordination (`contributions/`, `inboxes/`, `specialist-state/`). These directories are not created.
2. **All standard session protocols apply unchanged.** The session startup protocol (Steps 1–5, 11), session conduct rules from SKILL.md, and the session close protocol execute identically to any single-agent session. There is no reduced functionality.
3. **No multi-agent sections in session history.** Because no specialists participated, the session history file omits the Multi-Agent Contributions section (§10). All other session history sections (Agenda, Decisions, Artifacts, Open Questions) are written normally.
4. **Subagent dispatches remain available.** Single-agent fallback affects only the peer-specialist model (multi-agent mode). The group lead may still dispatch subagents for discrete tasks (e.g., invoking skills like `memory-retriever`) as it would in any standard session. These are recorded in the Subagent Dispatches section of session history, not in Multi-Agent Contributions.

### 11.3 No Degraded Experience

Single-agent fallback is not an error state or a reduced-capability mode. It is the default operating mode for sessions that do not need parallel specialist work. The user should experience no difference in session quality, available features, or output completeness compared to sessions that were never offered multi-agent mode in the first place.

If the fallback was triggered by specialist failure (rather than user choice), the group lead reports which specialists failed and why, then proceeds normally. The tasks that would have been assigned to specialists are handled directly by the group lead during the active discussion phase.
