# Setup Guide

This guide walks through setting up research-session on a fresh machine. It is written for both human users and AI agents (Claude Code, Codex, etc.).

## Prerequisites

| Requirement | Check command | Notes |
|-------------|--------------|-------|
| Claude Code CLI | `claude --version` | Or any agent runtime that supports SKILL.md instructions |
| Git | `git --version` | For cloning this repo |

### Recommended companion skills

| Skill | Type | What happens without it |
|-------|------|------------------------|
| [memory-skill](https://github.com/ChenShizhe/memory-skill) | Hard dependency (degraded mode) | Session startup skips identity loading and expanded instructions. All other features work. |
| [paper-reader](https://github.com/ChenShizhe/paper-reader) | Soft dependency | Literature pipeline features are unavailable. Core research discussion works fine. |

**No Python dependencies.** This skill is pure SKILL.md instructions with protocol and template files.

## Step 1: Clone the repo

```bash
git clone https://github.com/ChenShizhe/research-session.git
cd research-session
```

## Step 2: Create a project workspace

Research projects can live anywhere on disk. The skill resolves the project root at session start from your input — you can provide a bare name or a full path. `~/Documents/Research/` is one default lookup location for bare names, but you can use any directory.

Create your first project:

```bash
mkdir -p ~/Documents/Research/my-project
```

**Windows equivalent:**
```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\Documents\Research\my-project"
```

## Step 3: Install the skills

```bash
SKILL_DIR=~/.claude/skills
mkdir -p "$SKILL_DIR"

cp -R research-meeting "$SKILL_DIR/research-meeting"
cp -R session-handoff "$SKILL_DIR/session-handoff"
```

## Step 4: Verify

Start a Claude Code session in your project directory and say:

> "Start a research session on [your topic]."

**Done signal (full mode):** If memory-skill is installed, you should see the agent load your identity files and print a session-start summary. If memory-skill is absent, it will warn about degraded mode and proceed — that is correct behavior.

**Done signal (degraded mode):** The agent says it is running in degraded mode (no core identity files) and proceeds to set up the session. This confirms the skill is installed and working.

## Cross-Platform Notes

- **macOS / Linux:** Works out of the box.
- **Windows:** Use `%USERPROFILE%\Documents\Research\` or any other directory for project workspaces. All protocol and template files are plain markdown — no platform-specific code.

## Customizing Specialist Roles

The `research-meeting/roles/` directory contains generic specialist templates:

- `code-specialist.md` — implementation and testing
- `literature-specialist.md` — paper screening and synthesis
- `theory-specialist.md` — mathematical reasoning and proof checking
- `external-reviewer.md` — independent review

Copy and edit these for your domain. For persistent customization, store refined roles in your central memory and let memory-manager evolve them over time.

## What to do next

1. Start a research session and discuss a topic.
2. At the end, invoke `session-handoff` to generate a `handoff.md` for next time.
3. In the next session, provide the handoff and the agent resumes where you left off.
