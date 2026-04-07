# research-session

Two complementary skills for managing persistent, multi-session research discussions with AI agents.

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

Research projects live under `~/Documents/Research/<project-name>/`. Each project directory is created on first use.

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
