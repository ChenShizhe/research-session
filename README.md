# research-session

Two complementary skills for managing persistent, multi-session research discussions with AI agents. Built as model-agnostic markdown instructions that any LLM agent runtime can follow.

## Prerequisites

- Git
- Claude Code or compatible agent runtime that supports SKILL.md instructions

## Quick Start

```bash
git clone https://github.com/ChenShizhe/research-session.git
cd research-session
mkdir -p ~/Documents/Research/my-project   # project workspace (anywhere on disk)
mkdir -p ~/.claude/skills
cp -R research-meeting ~/.claude/skills/research-meeting
cp -R session-handoff  ~/.claude/skills/session-handoff
```

See [SETUP.md](SETUP.md) for the full walkthrough including companion skill setup and cross-platform notes.

## Usage Example

Start a Claude Code session and say:

> "Start a research session on [topic]."

The agent bootstraps context from prior sessions and core memory, then opens a persistent discussion you can checkpoint, branch into specialist sub-agents, or close with a handoff for next time.

## Skills Included

### research-meeting

Session coordinator for persistent research discussions. Handles:

- **Session lifecycle** — startup bootstrap, context checkpoints, close protocol
- **Multi-agent mode** — optional specialist agents (code, theory, literature, reviewer) with structured collaboration
- **Literature pipeline** — living review, paper screening, synthesis integration
- **Health digest** — project health monitoring across code, literature, and tasks
- **Voice input** — domain-aware speech-to-text correction via per-project glossaries

### session-handoff

Generates a concise `handoff.md` at session end so the next session can resume with full context. User-invoked only — never auto-triggered.

## Installation

Copy both skill directories to your agent's skill root:

```
<your-skill-root>/
├── research-meeting/
│   ├── SKILL.md
│   ├── protocols/
│   ├── roles/
│   └── templates/
└── session-handoff/
    └── SKILL.md
```

## Configuration

### Project workspace

Research projects can live anywhere on disk. At session start, the skill resolves the project root from your input — you can provide a bare name (e.g., "Hawkes") or a full path (e.g., `~/my-projects/hawkes/`). Bare names are looked up in `~/Documents/Research/` and `~/Documents/Playground/projects/` by default. See SKILL.md for the full priority chain.

### Core memory files

The startup protocol reads identity files from `~/Documents/memory/`:

- `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`

These are optional — the skill runs in degraded mode if they are absent.

### Specialist roles

The `roles/` directory contains generic specialist templates. To customize:

1. Copy and edit the role files for your domain
2. For persistent personalization, store refined roles in your central memory under `roles/` and use experience-logger + memory-manager to evolve them over time

## Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| memory-retriever (from [memory-skill](https://github.com/ChenShizhe/memory-skill)) | hard (degraded mode available) | Context bootstrap at session start, mid-session recall |
| session-handoff | soft | Handoff generation at session end |
| experience-logger (from [memory-skill](https://github.com/ChenShizhe/memory-skill)) | soft | Session experience logging at close |
| paper-reader / paper-discovery (from [paper-reader](https://github.com/ChenShizhe/paper-reader)) | soft | Literature pipeline integration |

If a soft dependency is unavailable, the skill warns and proceeds without it. If memory-retriever is unavailable, the startup protocol runs in degraded mode — core identity and expanded instructions are skipped, but project context, discussion, and all other features work normally.

## License

MIT
