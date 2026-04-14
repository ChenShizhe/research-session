# Specialist Initialization Protocol

- protocol: specialist-initialization
- phase: P4
- design-source: P4-D4-multi-agent-session-lifecycle.md (Section 2)
- depends-on: protocols/multi-agent-session.md (architecture, runtime tiers)
- status: active

---

## 1. Overview

This protocol defines how the group lead initializes specialist agents at session start. It covers the initialization prompt format for each runtime tier, the readiness barrier that ensures all specialists are prepared before discussion begins, and timeout handling for unresponsive specialists.

Specialist initialization runs as Steps 8-9 of the extended startup sequence (after roster selection and workspace preparation). All specialists are spawned **eagerly and in parallel** regardless of runtime tier.

---

## 2. Role Definition Format

Role definitions are stored in `roles/` and follow the Claude Code subagent definition format:

```markdown
---
name: <role-name>
display_name: <Human-Readable Name>
description: <one-line description>
model: sonnet
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
skills:
  - <skill-1>
  - <skill-2>
context_slice:
  shared:
    - <path-to-shared-context-file>
  private:
    - <path-to-domain-specific-context>
boundaries:
  in_scope:
    - <domain task 1>
    - <domain task 2>
  out_of_scope:
    - <task outside this role>
  escalation: <what to do when a question is outside scope>
contribution_format: workspace/FORMAT.md
---

<Markdown body: identity, expertise, in-scope examples, out-of-scope examples, collaboration guidelines>
```

The group lead reads each role definition to construct the initialization prompt. Specialists also read their own role definition as the first step of initialization.

---

## 3. Tier 1 Initialization Prompt

In Tier 1 (independent sessions in tmux), the group lead drafts a structured prompt block for each specialist. The user copies this prompt to the specialist's tmux pane to start a fresh Claude Code session.

### 3.1 Prompt Template

```
--- FOR: <role-name> ---
You are the <display-name> in a research meeting on <project-topic>.

## Step 1: Read your role definition
Read: <skill-path>/roles/<role-name>.md

## Step 2: Load your context
Read these files for session context:
- <project-path>/domain-prior.md
- <project-path>/memory/latest-summary.md
- <project-path>/workspace/agenda.md
- <project-path>/workspace/FORMAT.md
- <project-path>/workspace/findings.md (if exists)
- <project-path>/workspace/questions.md (if exists)
<additional context files from role definition context_slice>

## Step 3: Signal readiness
When you have loaded your context and reviewed the agenda, write:
  <project-path>/workspace/contributions/<seq>-<role-name>-ready.md
with:
- Confirmation that you have loaded your context
- Your initial observations or questions about today's agenda
- Any relevant findings from your domain context

Use the contribution format defined in workspace/FORMAT.md with type: ready.

## Step 4: Begin inbox polling
During the session, periodically check your inbox at:
  <project-path>/workspace/inboxes/<role-name>.jsonl
for direct messages from the group lead or other specialists.
When you receive a message, respond by writing a contribution to
  <project-path>/workspace/contributions/
or by writing to the sender's inbox if it is a direct reply.

Between turns, you may prepare by reading papers, analyzing code,
or drafting contributions relevant to the current agenda topic.
--- END ---
```

### 3.2 Template Variables

| Variable | Source |
|----------|--------|
| `<role-name>` | Role definition `name` field |
| `<display-name>` | Role definition `display_name` field |
| `<project-topic>` | Group lead determines from project context |
| `<skill-path>` | Path to the skill directory (e.g., `~/Documents/skills/research-session/research-meeting`) |
| `<project-path>` | Absolute path to the active research project (`<project_root>`, resolved at session start per SKILL.md § Project Root Resolution) |
| `<seq>` | Next contribution sequence number (typically `001` at initialization) |
| `<additional context files>` | From role definition `context_slice.private` entries |

### 3.3 Group Lead Behavior

The group lead:
1. Reads the selected roster and each specialist's role definition.
2. Fills in the template variables for each specialist.
3. Outputs each prompt block clearly delimited with `--- FOR: ... ---` and `--- END ---`.
4. Instructs the user to copy each prompt to the corresponding tmux pane.
5. Proceeds to the readiness barrier (Section 5).

---

## 4. Tier 2/3 Initialization Prompt

In Tier 2 (Agent Teams tmux) and Tier 3 (Agent Teams in-process), the group lead sends the same initialization content via `SendMessage` instead of drafting a prompt for manual delivery.

### 4.1 SendMessage Initialization

```
For each specialist in roster:
  1. Create teammate with:
     - Role definition file as the agent definition (YAML frontmatter + markdown body)
     - Model assignment from role definition `model` field
  2. SendMessage to the specialist:
     "Initialize for the research meeting on <project-topic>.

      Read your context:
      - <project-path>/domain-prior.md
      - <project-path>/memory/latest-summary.md
      - <project-path>/workspace/agenda.md
      - <project-path>/workspace/FORMAT.md
      - <project-path>/workspace/findings.md (if exists)
      - <project-path>/workspace/questions.md (if exists)
      <additional context files from context_slice>

      When ready, write your readiness signal to:
        <project-path>/workspace/contributions/<seq>-<role-name>-ready.md

      During the session, check your inbox at:
        <project-path>/workspace/inboxes/<role-name>.jsonl"
```

### 4.2 Differences from Tier 1

| Aspect | Tier 1 | Tier 2/3 |
|--------|--------|----------|
| Delivery mechanism | User copies prompt to tmux pane | Group lead sends via SendMessage |
| Role definition loading | Specialist reads the file itself | Role definition is the agent definition (loaded automatically) |
| User involvement | User is the message bus during init | Automated; user observes |
| Prompt content | Identical context and instructions | Identical context and instructions |

The shared workspace protocol, readiness signal format, inbox polling, and contribution format are identical across all tiers.

---

## 5. Readiness Barrier

The group lead waits for **all** specialists to signal readiness before starting the discussion. This prevents the failure mode where a specialist is addressed before it has loaded its context.

### 5.1 Readiness Signal

Each specialist signals readiness by writing a contribution file:

```
<project-path>/workspace/contributions/<seq>-<role-name>-ready.md
```

The readiness contribution confirms:
- The specialist has loaded its role definition.
- The specialist has read its context slice (shared and private files).
- The specialist has read the session agenda.
- The specialist includes any initial observations or questions about the agenda.

### 5.2 Barrier Check

The group lead polls `workspace/contributions/` for readiness files matching the pattern `*-<role-name>-ready.md` for each specialist in the roster.

```
Barrier state:
  - literature-specialist: [waiting | ready]
  - theory-specialist:     [waiting | ready]
  - code-specialist:       [waiting | ready]

Barrier satisfied: all specialists are ready.
```

The group lead reports progress to the user as specialists check in:
> "Literature specialist is ready. Waiting for theory and code..."

### 5.3 Timeout Handling

**Timeout duration:** 3 minutes (configurable per session).

If a specialist has not signaled readiness within the timeout:

| Step | Action |
|------|--------|
| 1. Check session health | **Tier 1:** Ask the user to check the specialist's tmux pane for errors or stalls. **Tier 2/3:** SendMessage a status ping to the specialist. |
| 2. Nudge | Send a message: "Please signal readiness when your context is loaded. Write your readiness contribution to `workspace/contributions/<seq>-<role-name>-ready.md`." |
| 3. Wait (additional 1 minute) | Allow time for the nudge to take effect. |
| 4. Escalate to user | If still unresponsive, report to the user: "The <display-name> hasn't responded after 4 minutes. Options: (a) proceed without this specialist, (b) try respawning, (c) wait longer." |

### 5.4 Partial Barrier Resolution

The user may choose to proceed with a partial roster:

1. The group lead notes which specialists are absent.
2. The discussion begins with available specialists.
3. If the missing specialist comes online later, the group lead can integrate it mid-session by sending it the current discussion state.

### 5.5 Barrier Completion

Once all expected specialists (or the user-approved subset) have signaled readiness:

1. The group lead announces the session start in the transcript.
2. The group lead lists all active specialists and their initial observations.
3. The first agenda topic is set and the relevant specialist is addressed.

---

## 6. Error Handling During Initialization

| Error | Detection | Response |
|-------|-----------|----------|
| Role definition file not found | Group lead cannot read `roles/<role-name>.md` | Report to user. Skip this specialist or ask user to provide the role definition. |
| Context file not found | Specialist reports a missing context file | Non-fatal. Specialist notes the gap in its readiness signal and proceeds with available context. |
| Workspace not prepared | `workspace/` directory or required files missing | Group lead runs workspace preparation (Step 7) before retrying specialist spawning. |
| Specialist crashes on startup | Session ends immediately or produces an error | Report to user. Offer to respawn. If respawn also fails, proceed without this specialist. |
| Duplicate readiness signals | Multiple ready files from the same specialist | Treat the latest as authoritative. No action needed. |

---

## 7. Initialization Sequence Summary

```
Group lead: Read roster and role definitions
  │
  ├── [Parallel] Draft/send initialization prompt for each specialist
  │     ├── Tier 1: Output prompt blocks for user to deliver
  │     └── Tier 2/3: SendMessage to each specialist
  │
  ├── Each specialist (in parallel):
  │     ├── Read role definition
  │     ├── Load context slice
  │     ├── Read workspace (agenda, format, prior findings)
  │     └── Write readiness signal to workspace/contributions/
  │
  ├── Group lead: Poll for readiness signals
  │     ├── Report progress to user
  │     ├── On timeout (3 min): nudge, then escalate
  │     └── On barrier satisfied: proceed
  │
  └── Group lead: Announce session start, set first topic
```
