# Multi-Agent Session Protocol

- protocol: multi-agent-session
- phase: P4
- design-source: P4-D1-multi-agent-session-architecture.md
- status: active

---

## 1. Architecture Overview

The multi-agent session uses a **hub-and-spoke + shared blackboard hybrid**.

```
                    +-----------------+
                    |   Group Lead    |
                    |  (Coordinator)  |     <- Hub: manages discussion, synthesizes
                    +--------+--------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v-----+  +-----v------+
     | Literature  |  |  Theory/   |  |   Code     |     <- Spokes: persistent specialists
     | Specialist  |  |   Proof    |  | Specialist |
     +------+------+  +-----+-----+  +-----+------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    | Shared Workspace |     <- Blackboard: structured contributions
                    |   (File-based)   |
                    +------------------+
```

**Hub (Group Lead):** The primary Claude Code session. Manages discussion flow, synthesizes contributions, makes delegation decisions, maintains the canonical transcript, and runs session startup/close protocols.

**Spokes (Specialists):** Persistent agents with domain expertise. Each runs as an independent full session (not a subagent). Specialists contribute findings within their domain, read the shared workspace to stay aware of discussion state, signal when they have relevant input, and prepare in parallel while other specialists speak.

**Blackboard (Shared Workspace):** A directory of structured files serving as the canonical coordination backbone. All agents read from and write to this space. The shared workspace protocol is identical across all runtime tiers.

### 1.1 Why This Hybrid

- **Pure hub-and-spoke** creates a coordinator bottleneck: the group lead's context bears the full load of relaying information between specialists.
- **Pure blackboard** lacks coordination control: without a moderator, agents produce redundant contributions or talk past each other.

The hybrid addresses both: the group lead maintains discussion control (turn management, synthesis), while the shared workspace provides a direct channel for specialist contributions without requiring the group lead to relay every piece of information.

### 1.2 What "Persistent" Means

A persistent specialist:
1. Initializes at session start with its domain-specific context slice.
2. Remains available throughout the session -- can be addressed at any point.
3. Maintains its own conversation history and reasoning context across multiple contributions.
4. Terminates at session close and logs its contributions.

Specialists are **independent full agent sessions**, not subagents constrained by a parent. Each has its own context window, full tool access, and peer-level autonomy. This enables peer-to-peer communication, crash isolation, and autonomous contribution.

---

## 2. Communication Channels

Three channels operate simultaneously. All three are available in every runtime tier.

### 2.1 Channel 1: Directed Messages (Group Lead <-> Specialist)

Used for directing questions, requesting input, providing context, and steering discussion.

Implementation varies by runtime tier:
- **Tier 1:** Group lead drafts a structured prompt block; user delivers it to the specialist's session.
- **Tier 2/3:** Group lead sends via SendMessage.

Example directed message:
> "Literature specialist: what bandwidth selectors have been studied for kernel-smoothed cross-covariance estimators? Focus on methods applicable to multivariate point processes."

### 2.2 Channel 2: Peer-to-Peer Messages (Specialist <-> Specialist)

Used for direct challenges, urgent cross-domain information, and requests for specific input. Implemented via per-specialist inbox files in the shared workspace.

The group lead does NOT mediate every inter-specialist exchange. Peer messages are also logged to the shared workspace (Channel 3), so the group lead and user can see them in the transcript.

Example:
> "The convergence rate in your contribution #4 assumes bounded intensity. Author (Year, Theorem 3.2) shows this fails for clustered processes. Check `workspace/contributions/007-literature-specialist-challenge.md`."

### 2.3 Channel 3: Shared Workspace (All Agents -> Workspace Files)

Used for recording contributions, findings, questions, and challenges. Implemented via file I/O. Each specialist writes to its own contribution files (no concurrent write conflicts). The group lead reads contributions and integrates them into the discussion transcript.

> **Note:** The shared workspace file structure and contribution format are defined in a separate document (M9 scope). This protocol defines the communication patterns, not the file layout.

---

## 3. Turn Management

The group lead controls turn order. Turn management is **judgment-based**, not round-robin, informed by the current discussion topic.

### 3.1 Turn Assignment Rules

| Situation | Group Lead Action |
|-----------|------------------|
| Topic is within one specialist's domain | Address that specialist directly |
| Topic spans multiple domains | Address each specialist in sequence, then synthesize |
| Specialist signals it has something to add | Acknowledge and give it the floor |
| Discussion is between user and group lead | Specialists wait (they may prepare in parallel) |
| No specialist input is needed | Continue without involving specialists |

### 3.2 Request-to-Speak

A specialist can signal a desire to contribute by writing a contribution with `type: request-to-speak` to the shared workspace. The group lead decides whether to yield the floor.

This mechanism prevents specialists from interrupting when the user and group lead are reasoning through something. The group lead always has the final say on turn order.

### 3.3 Parallel Preparation

Specialists are not idle between turns. While waiting, specialists can:
- Read papers or code relevant to the current topic.
- Prepare analysis they expect will be needed.
- Search the project vault for relevant notes.
- Write draft contributions to their staging area.

This happens naturally in Tier 1 and Tier 2 (each specialist is an independent session). In Tier 3 (in-process), it depends on the runtime's concurrency model.

---

## 4. Runtime Strategy

The architecture is **runtime-agnostic at the protocol level.** The shared workspace protocol works identically regardless of how agents are deployed. The runtime tier determines how messages are delivered and how specialists are managed.

### 4.1 Tier 1: Independent Sessions in tmux (Recommended)

**Requirements:** tmux installed.

**How it works:**
- The user starts multiple Claude Code sessions in tmux panes (or separate terminal windows).
- Each specialist is a fully independent Claude Code session with its own context window, tools, and session identity.
- The group lead session runs in one pane; each specialist gets its own pane.
- All coordination happens through the shared workspace (files).
- Each specialist reads a role definition file as its system prompt or initial instruction.
- The group lead drafts specialist prompts; the user delivers them to the appropriate pane. Over time, specialists also poll their inbox files and the workspace autonomously.

**Why Tier 1 is recommended:**
1. **Full autonomy.** Each specialist has its own 1M-token context, full tool access (including the Agent tool for further delegation), and no constraints imposed by a parent-child relationship.
2. **Peer-to-peer communication.** Specialists write direct messages to each other's inbox files -- no parent relay bottleneck.
3. **Crash isolation.** One specialist crashing does not affect others. The shared workspace preserves all prior contributions.
4. **No experimental feature dependency.** Works with any Claude Code version. No Agent Teams flag needed.
5. **Direct user access.** The user can switch to any specialist's pane and interact with it directly.
6. **Full session capabilities.** Each specialist can use `/resume`, load skills, access MCP servers, and do anything a normal Claude Code session can do.

**Group lead prompt drafting protocol:**
When the group lead wants to address a specialist, it produces a structured prompt block:

```
--- FOR: literature-specialist ---
Read the shared workspace at <project>/workspace/transcript.md
for current discussion context, then:

[Specific question or task for the specialist]

Write your contribution to:
<project>/workspace/contributions/<seq>-literature-specialist-<type>.md
following the contribution format in workspace/FORMAT.md.
--- END ---
```

The user copies this to the specialist's session. As the session evolves, specialists also monitor their inbox files and the workspace autonomously, reducing the need for manual relay.

### 4.2 Tier 2: Agent Teams -- tmux Mode

**Requirements:** tmux installed, Agent Teams feature enabled.

**How it works:**
- Group lead creates a team and spawns specialists as teammates in tmux panes.
- Teammates are full Claude Code sessions with SendMessage for direct communication.
- Shared workspace files serve the same role as in Tier 1.

**When to use:** When the user prefers automated message delivery (SendMessage) over manual prompt copying. Agent Teams adds convenience at the cost of framework constraints.

**Limitations:**
- Agent Teams is experimental -- behavior may change across versions.
- Session resume drops in-process teammates (tmux mode mitigates this but team state may still be lost).
- One team per session; no nested teams.

### 4.3 Tier 3: Agent Teams -- In-Process Mode

**Requirements:** Agent Teams feature enabled. No tmux needed.

**How it works:**
- Group lead spawns specialists as in-process teammates.
- Communication via SendMessage + shared workspace.
- Simplest setup.

**Limitations:**
- Specialists cannot use the Agent tool.
- Session resume drops in-process teammates.
- All agents share rate limits more tightly.
- Suitable only for shorter, simpler multi-agent sessions where specialists don't need to delegate.

### 4.4 Runtime Selection Guide

| Condition | Recommended Tier |
|-----------|-----------------|
| tmux available (general case) | **Tier 1** (independent sessions) |
| tmux available + Agent Teams enabled + user prefers automated messaging | Tier 2 (Agent Teams tmux) |
| No tmux, Agent Teams enabled | Tier 3 (in-process) |

The shared workspace protocol is identical across all tiers. The variable is the message delivery mechanism: manual copy-paste (Tier 1), SendMessage (Tiers 2-3), or autonomous inbox polling (all tiers).

---

## 5. Cost Model

### 5.1 Model Assignment

| Role | Model | Rationale |
|------|-------|-----------|
| Group Lead (Coordinator) | Opus | Best reasoning for synthesis, turn management, and discussion control. Worth the premium for the single coordinator. |
| Specialists | Sonnet | Good domain reasoning at lower cost. 1M-token context is sufficient for session-long persistence. |
| One-shot subagents (delegated by specialists) | Sonnet or Haiku | Haiku for exploration/search. Sonnet for reasoning tasks. |

### 5.2 Token Cost Profile

A multi-agent session with 1 Opus coordinator + 3 Sonnet specialists uses approximately 7-15x the tokens of a single-agent session. For a 1-hour session:
- **Single-agent baseline:** ~100-200k tokens.
- **Multi-agent (4 agents):** ~700k-3M tokens across all agents.

Primary cost drivers:
1. Specialist context initialization (loading project context into each specialist).
2. Repeated shared workspace reads (each specialist reads the transcript to stay current).
3. Coordinator synthesis (reading and integrating all specialist contributions).

### 5.3 Structural Budget Controls

The skill does not enforce hard token budgets. Instead, the design uses structural controls to manage cost:

1. **Lazy specialist engagement.** Specialists are initialized eagerly (present from session start), but the group lead only engages them when their domain is relevant. Idle specialists consume minimal tokens.
2. **Contribution brevity norms.** Specialist contributions have recommended length guidelines. The group lead can ask for shorter contributions if the discussion is consuming too much context.
3. **Specialist parking.** If a specialist is not needed for an extended portion of the discussion, the group lead sends a "stand by until called" message. The specialist stops reading the workspace until re-engaged.
4. **Session duration awareness.** Long sessions (>2 hours) risk context overflow for specialists with heavy participation. The group lead should suggest a session close and restart if specialists' context windows are approaching limits.

---

## 6. Specialist-Initiated Context Rotation

When a specialist detects its context window is approaching saturation (e.g., heavy participation over a long session), it may request a context rotation:

1. The specialist writes a `type: context-rotation-request` contribution to the shared workspace, summarizing its accumulated reasoning and key conclusions.
2. The group lead reviews the request and presents it to the user for approval.
3. If approved, the specialist's session is terminated and a new session is started with: the role definition, the shared workspace state, and the specialist's self-summary.
4. The new session picks up where the old one left off, with a fresh context window.

Context rotation requires user approval because it involves ending and restarting a specialist session. The group lead cannot unilaterally rotate a specialist.

---

## 7. Kill Criteria for Stuck Specialists

A specialist is considered stuck when it exhibits any of the following:

1. **Repeated argument loop (3+ cycles).** The specialist repeats the same argument or position three or more times without new evidence or reasoning. The group lead intervenes with: "You've made this point three times. Either provide new evidence or defer to the group."
2. **No progress on assigned task.** The specialist has been working on a task for an extended period without producing a contribution or status update. The group lead checks in and may reassign the task.
3. **Persistent tool failures.** The specialist encounters repeated tool failures (e.g., file not found, API errors) and cannot work around them. The group lead may park the specialist and proceed without it.

When a specialist is determined to be stuck, the group lead has three options:
- **Redirect:** Give the specialist a different question or perspective.
- **Park:** Tell the specialist to stand by until a more relevant topic arises.
- **Terminate:** End the specialist's session if it is no longer contributing value. Its existing workspace contributions are preserved.

---

## 8. One-Shot Delegation Coexistence

Phase 3 one-shot delegation is not replaced by persistent specialists -- the two patterns coexist and serve different purposes.

### 8.1 When to Use Each Pattern

| Pattern | Use When |
|---------|----------|
| **Persistent specialist** | Ongoing discussion participation requiring accumulated context. The specialist builds on prior reasoning across multiple turns. |
| **One-shot subagent** | Bounded task with clear input and output. No need for session-long presence. Examples: reading a specific paper, running a code analysis, generating a diagram. |

### 8.2 Who Can Delegate One-Shot Subagents

- **Group lead:** Can spawn one-shot subagents for bounded tasks at any time, exactly as in Phase 3.
- **Specialists (Tier 1 and Tier 2):** Can spawn their own one-shot subagents for bounded tasks within their domain. For example, the literature specialist may spawn a paper-reader subagent to extract findings from a specific paper.
- **Specialists (Tier 3):** Cannot use the Agent tool; must request the group lead to delegate on their behalf.

### 8.3 Delegation Decision Flow

```
Is this a bounded task with clear input/output?
  YES -> One-shot subagent (Phase 3 delegation)
  NO  -> Does it require ongoing discussion participation?
    YES -> Persistent specialist (this protocol)
    NO  -> Group lead handles it directly
```

### 8.4 Interaction Between Patterns

- A persistent specialist may request one-shot delegation via the group lead or (in Tier 1/2) delegate directly.
- One-shot subagents spawned by a specialist report back to that specialist, not to the group lead.
- The group lead sees the results only when the specialist writes them to the shared workspace.
- One-shot subagents do not read from or write to the shared workspace directly -- they report to their spawner.

---

## 9. Specialist Roster

The specialist roster is not hardcoded. A roster configuration defines which specialists to activate for a given session. The starter roster is:

1. **Literature Specialist** -- paper search, citation analysis, related work synthesis.
2. **Theory/Proof Specialist** -- proof construction, asymptotic analysis, convergence rates.
3. **Code Specialist** -- simulation code, result analysis, debugging, implementation.

The user can create new specialist definitions with the group lead's help. Role definitions are stored in `roles/` and follow a consistent schema (see specialist role definition documents).

---

## 10. Constraints and Non-Goals

**Constraints:**
- The multi-agent protocol must work with all three runtime tiers using the same shared workspace.
- Model recommendations are provider-agnostic -- Claude names (Opus, Sonnet) are examples.

**Non-goals for this protocol:**
- Shared workspace file structure and contribution format (M9 scope).
- Session lifecycle amendments for multi-agent startup/close (M9 scope).
- Phase 5 features.
- Actually running multi-agent sessions.
