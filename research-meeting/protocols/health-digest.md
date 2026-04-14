# Health Digest Generation Protocol

## Purpose

Generate a periodic, quantitative snapshot of project health. The digest surfaces staleness, drift, and scope creep so the user (or session startup) can orient quickly without reading every project file.

---

## Design Principles

1. **Metrics first, summary second.** Deterministic shell commands collect raw metrics into structured JSON. The LLM reads that JSON and produces a natural-language digest. The LLM adds narrative, not data.
2. **Delta-oriented, exception-driven.** Every metric is presented as current value plus change since the last digest. The digest is short when everything is on track; its length correlates with the number of issues, not the number of metrics.
3. **Read-only for project files.** The digest system reads all project files but writes only to `digests/`. It never modifies `tasks.md`, `memory/latest-summary.md`, manuscript files, code, or any other project artifact.

---

## Core Invariant

The health digest system has **read-only access to all project files** and **write-only access to the `digests/` directory**. Its only side effects are two files per run:

| Output | Purpose |
|--------|---------|
| `digests/YYYY-MM-DD.json` | Structured metrics for delta computation and programmatic analysis |
| `digests/YYYY-MM-DD.md` | Human-readable narrative digest for session startup and user reading |

The JSON is the source of truth. The markdown is a rendering of the JSON by the LLM. If the `digests/` directory does not exist, the subagent creates it -- this is the single exception to "read-only outside digests."

---

## Metric Categories

Five categories. Each metric specifies what is measured, the shell command that collects it, and the staleness threshold that triggers an alert. All thresholds are configurable in `health-config.yaml`; defaults are listed here.

### 1. Manuscript

| Metric | Collection Method | Staleness Threshold |
|--------|------------------|---------------------|
| Word count by section | `texcount -inc -sub=section manuscript/main.tex` | n/a (trend metric) |
| Section completion % | Parse `texcount` output: sections with >100 words = in progress; sections with 0 words = not started. % = started / expected. | n/a (progress metric) |
| Days since last edit | `git log --format="%aI" -1 -- manuscript/` | **14 days** = warning; **30 days** = stale |

**Shell commands:**

```bash
# Word count by section (requires texcount)
texcount -inc -sub=section -template="{SUM}" manuscript/main.tex 2>/dev/null

# Last edit date
git log --format="%aI" -1 -- manuscript/ 2>/dev/null \
  || stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" manuscript/*.tex 2>/dev/null
```

**Degraded mode:** If `texcount` is not installed, fall back to `wc -w manuscript/*.tex` (no section breakdown). The digest notes the degraded mode.

### 2. Code

| Metric | Collection Method | Staleness Threshold |
|--------|------------------|---------------------|
| Test coverage (R) | `Rscript -e "cat(covr::percent_coverage(covr::package_coverage()))"` | n/a (trend metric) |
| Test coverage (Python) | `coverage run -m pytest && coverage json -o /dev/stdout` | n/a (trend metric) |
| Lint warnings (R) | `Rscript -e "cat(length(lintr::lint_dir('code/')))"` | n/a (trend metric) |
| Lint warnings (Python) | `ruff check code/ --output-format json` piped to count | n/a (trend metric) |
| Last commit date | `git log --format="%aI" -1 -- code/` | **7 days** (active); **30 days** (maintenance) |

**Shell commands:**

```bash
# Last commit date
git log --format="%aI" -1 -- code/ 2>/dev/null

# R test coverage (if R project)
Rscript -e "cat(covr::percent_coverage(covr::package_coverage()))" 2>/dev/null

# Python test coverage (if Python project)
cd code/ && coverage run -m pytest -q 2>/dev/null \
  && coverage json -o - 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['totals']['percent_covered'])"

# R lint count
Rscript -e "cat(length(lintr::lint_dir('code/')))" 2>/dev/null

# Python lint count
ruff check code/ --output-format json 2>/dev/null \
  | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
```

**Degraded mode:** If `covr`, `coverage.py`, `lintr`, or `ruff` are not installed, those metrics are omitted with a note (e.g., "Test coverage metric unavailable (covr not installed)"). Remaining metrics (commit date, file counts) are always available.

### 3. Simulations

| Metric | Collection Method | Staleness Threshold |
|--------|------------------|---------------------|
| Completed / planned ratio | Count output files in `results/` matching configured patterns vs. planned count | n/a (progress metric) |
| Failed job count | Local: count `*.err`/`*.fail` in `results/`. Slurm: `sacct --state=FAILED` | Any failure **>3 days** old without resolution |
| Last run date | Most recent modification time in `results/` | Project-dependent (configured) |

**Shell commands:**

```bash
# Count result files
ls results/ 2>/dev/null | wc -l

# Find most recent result
stat -f "%m %N" results/* 2>/dev/null | sort -rn | head -1

# Check for failures (local)
ls results/*.err results/*.fail 2>/dev/null | wc -l

# Check for failures (Slurm, if available)
sacct -u $USER --state=FAILED \
  --starttime=$(date -v-7d +%Y-%m-%d) \
  --format=JobID,JobName,State --noheader 2>/dev/null | wc -l
```

**Degraded mode:** If the project has no `results/` directory, the Simulations section is omitted entirely. If a remote HPC server is configured but unreachable, the digest notes: "Simulation status unavailable (remote server not reachable)." Local files are still checked.

### 4. Literature

| Metric | Collection Method | Staleness Threshold |
|--------|------------------|---------------------|
| Papers in collection | Count `.bib`/`.pdf` in `references/`. If P5-D1 pipeline manifest exists, use richer counts. | n/a (cumulative metric) |
| Vault coverage | Cross-reference `references/` against vault notes via frontmatter paths | n/a (coverage metric) |
| Last search date | Pipeline manifest `statistics.last_watcher_run`, or `git log` on `references/` | **30 days** since last search |

**Shell commands:**

```bash
# Count reference files
ls references/*.bib references/*.pdf 2>/dev/null | wc -l

# Read pipeline manifest if present
cat pipeline/manifest.json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('statistics',{})))"

# Last reference update
git log --format="%aI" -1 -- references/ 2>/dev/null
```

**Degraded mode:** Projects without a `references/` directory omit this section. If a P5-D1 pipeline manifest exists, use pipeline statistics; otherwise fall back to file-system counts.

### 5. Tasks

| Metric | Collection Method | Staleness Threshold |
|--------|------------------|---------------------|
| Open / total ratio | Parse `tasks.md` checkbox lines | n/a |
| Net task delta | Compare current open count against previous digest JSON | **3+ consecutive net positive deltas** = scope creep warning |
| Session recency | Most recent file in `sessions/` | **14 days** = dormant; **21 days** = stale |

**Shell commands:**

```bash
# Parse tasks.md
grep -c '^\s*- \[ \]' tasks.md 2>/dev/null   # open tasks
grep -c '^\s*- \[x\]' tasks.md 2>/dev/null    # completed tasks

# Session recency
ls -t sessions/*.md 2>/dev/null | head -1
```

**Degraded mode:** If `tasks.md` does not exist or uses a non-standard format, task metrics are omitted. The `health-config.yaml` `parser` field supports alternative formats.

---

## Staleness Threshold Summary

All thresholds are configurable per project in `health-config.yaml`. Defaults:

| Artifact Type | Warning Threshold | Stale Threshold |
|---------------|------------------|-----------------|
| Manuscript | 14 days since last edit | 30 days |
| Code (active development) | 7 days since last commit | 14 days |
| Code (maintenance mode) | 30 days since last commit | 60 days |
| Tasks (individual) | 21 days open without update | 42 days |
| Tasks (scope creep) | 3 consecutive net positive deltas | 5 consecutive |
| Literature | 30 days since last search | 60 days |
| Sessions | 14 days since last session | 30 days |

---

## Overall Status Logic

The overall status is determined by the number and severity of `[!]` alerts:

| Condition | Status |
|-----------|--------|
| 0 `[!]` alerts | **On Track** |
| 1-2 `[!]` alerts, none at "stale" severity | **Needs Attention** |
| 3+ `[!]` alerts, OR any "stale"-level threshold breached, OR no session in 30+ days | **Stalled** |

Alert generation is deterministic (performed in the data collection layer, not the LLM):

```
for each artifact_type in [manuscript, code, simulations, literature, sessions]:
    days = days_since_last_activity(artifact_type)
    warn_threshold = config.thresholds[artifact_type].warning
    stale_threshold = config.thresholds[artifact_type].stale

    if days >= stale_threshold:
        add_alert(severity="stale", message="...")
    elif days >= warn_threshold:
        add_alert(severity="warning", message="...")
```

---

## Graceful Degradation

The digest never fails due to a missing tool or absent artifact type. Rules:

1. **Missing directory** (e.g., no `code/`, no `results/`, no `references/`): omit the entire section. Do not show "N/A".
2. **Missing tool** (e.g., `texcount`, `covr`, `ruff` not installed): omit that specific metric. Include a note in the digest (e.g., "Test coverage metric unavailable (covr not installed)"). Other metrics in the same category are still collected.
3. **Missing `health-config.yaml`**: use skill-level defaults. All categories enabled if their directories exist.
4. **No previous digest** (first run): all deltas are `null`. The digest notes: "First digest for this project -- no deltas available."
5. **Command failure**: the command's JSON field is set to `null` with an `error` string explaining what happened. The digest continues with remaining commands.

---

## Data Collection Layer

### Principle

Data collection is deterministic shell commands only. No LLM involvement. The output is a single JSON file that serves as the contract between collection and summarization.

### Execution Order

The subagent executes collection commands in sequence by category (Manuscript, Code, Simulations, Literature, Tasks). Each command writes its output to a section of the metrics JSON. Commands that fail produce a `null` value with an `error` field.

### Delta Computation

Deltas are computed by the data collection layer, not the LLM. The subagent reads the most recent `.json` file from `digests/` and subtracts corresponding values. If no previous digest exists, all deltas are `null`.

### JSON Intermediate Format

The collection layer produces a single JSON file conforming to this schema:

```json
{
  "meta": {
    "project": "<project-name>",
    "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
    "digest_number": 7,
    "previous_digest": "YYYY-MM-DD",
    "project_root": "<project_root>"
  },
  "manuscript": {
    "available": true,
    "total_word_count": 8432,
    "sections": [
      {"name": "Introduction", "word_count": 1204, "status": "done"},
      {"name": "Methods", "word_count": 2847, "status": "in_progress"},
      {"name": "Results", "word_count": 312, "status": "draft"},
      {"name": "Discussion", "word_count": 0, "status": "not_started"}
    ],
    "last_edit": "YYYY-MM-DDTHH:MM:SSZ",
    "days_since_edit": 13,
    "delta": {
      "total_word_count": 847,
      "sections_changed": ["Methods", "Results"]
    },
    "alerts": [],
    "error": null
  },
  "code": {
    "available": true,
    "language": "R",
    "test_coverage_percent": 87.3,
    "lint_warnings": 4,
    "last_commit": "YYYY-MM-DDTHH:MM:SSZ",
    "days_since_commit": 2,
    "delta": {
      "test_coverage_percent": 2.1,
      "lint_warnings": -3
    },
    "alerts": [],
    "error": null
  },
  "simulations": {
    "available": true,
    "completed": 42,
    "planned": 50,
    "failed": 1,
    "last_run": "YYYY-MM-DDTHH:MM:SSZ",
    "days_since_run": 4,
    "failed_jobs": [
      {
        "id": "sim-042",
        "name": "experiment-run-042",
        "failed_at": "YYYY-MM-DDTHH:MM:SSZ",
        "error_file": "results/sim-042.err"
      }
    ],
    "delta": {
      "completed": 5,
      "failed": 1
    },
    "alerts": [
      {
        "severity": "warning",
        "message": "Failed job sim-042 unresolved for 4 days",
        "artifact": "results/sim-042.err"
      }
    ],
    "error": null
  },
  "literature": {
    "available": true,
    "papers_in_collection": 23,
    "vault_coverage": 18,
    "last_search": "YYYY-MM-DDTHH:MM:SSZ",
    "days_since_search": 18,
    "pipeline_status": null,
    "delta": {
      "papers_in_collection": 2
    },
    "alerts": [],
    "error": null
  },
  "tasks": {
    "available": true,
    "open": 8,
    "completed": 14,
    "total": 22,
    "net_delta": 1,
    "consecutive_positive_deltas": 2,
    "oldest_open_task": {
      "description": "Implement adaptive bandwidth selector",
      "age_days": 18
    },
    "last_session": "YYYY-MM-DDTHH:MM:SSZ",
    "days_since_session": 2,
    "delta": {
      "open": 1,
      "completed": 2
    },
    "alerts": [],
    "error": null
  },
  "previous_metrics": {
    "digest_date": "YYYY-MM-DD",
    "digest_file": "digests/YYYY-MM-DD.json"
  }
}
```

**Field rules:**
- If a category is unavailable (`available: false`), all fields except `available` and `error` are `null`.
- The `error` field is `null` on success, or a string describing why collection failed.
- Each category's `alerts` array is populated by the data collection layer based on threshold comparison. The LLM does not generate alerts -- it renders them.
- `delta` values are `null` when no previous digest exists.

---

## LLM Summarization Scope

The LLM receives the structured JSON and produces the markdown digest. Its responsibilities:

- Convert raw metrics into natural-language sentences with context.
- Generate the Suggested Actions section based on alerts and project state.
- Determine the Overall status classification using the status logic above.
- Decide which sections to collapse (no alerts, no significant deltas) vs. expand (alerts present).

The LLM does **NOT**:
- Collect any data. All data comes from the JSON intermediate.
- Fabricate metrics. Every number in the digest must originate from the JSON.
- Update any project files. The digest files are its only output.

---

## Scheduling

### Primary: Local Scheduled Tasks

The digest runs on the local machine (always-on desktop or server) with direct file system access to the project root.

**Desktop scheduled tasks (Claude Code):**
- Survives application restarts. Full local file system access.
- Setup: `/schedule weekly "Generate project health digest for <project-name>"`

**External scheduler (cron-compatible):**
- Jobs persist in the scheduler's configuration directory. Use isolated session targeting when available.
- The scheduled task prompt is **model-agnostic** and works with any compatible provider.
- Configure via the scheduler's interface with the scheduled task prompt template (see Execution Model below).

### Secondary: Cloud Scheduled Tasks

Cloud tasks are viable only for projects synced to a GitHub repository (cloud tasks cannot access local files).

### Ad-Hoc: On-Demand

The user or group lead can trigger a digest at any time: "Generate a health digest for this project." On-demand digests follow the same execution model and write to the same `digests/` directory.

---

## Execution Model: One-Shot Subagent

The digest is generated by a one-shot subagent following the P3-D1 delegation protocol.

### Delegation Profile

| Field | Value |
|-------|-------|
| Depth | Light (bounded data collection + summarization) |
| Mode | Background (scheduled or delegated by group lead) |
| Model | Sonnet |
| Max turns | 25 |
| Write scope | `digests/` directory only |

### Execution Steps

1. **Load configuration.** Read `health-config.yaml` for thresholds and metric settings. Fall back to defaults if absent.
2. **Read previous digest.** Find the most recent `.json` file in `digests/` for delta computation. If none exists, this is the first digest.
3. **Run data collection.** Execute shell commands per category. Capture stdout. Failed commands produce `null` with an error message.
4. **Structure metrics.** Assemble the JSON intermediate from command outputs. Compute deltas. Apply staleness thresholds. Generate alert entries.
5. **Write JSON.** Write `digests/YYYY-MM-DD.json`.
6. **Generate markdown.** Pass JSON to the LLM with digest template and format rules. The LLM produces the narrative.
7. **Write markdown.** Write `digests/YYYY-MM-DD.md`.
8. **Terminate.** No persistent state beyond the two files.

### Idempotency

If the digest runs twice on the same day, the second run overwrites the first. The filename `YYYY-MM-DD` ensures at most one digest per day.

### Scheduled Task Prompt Template

```
You are a project health monitor for the research project "<project-name>".

Project root: <project_root>/
Configuration: health-config.yaml (if present; use defaults otherwise)
Previous digests: digests/ directory

Execute the following steps:

1. Read health-config.yaml for thresholds and metrics configuration.
2. Find the most recent .json file in digests/ for delta computation.
3. Collect metrics by running shell commands:
   - Manuscript: texcount on manuscript/*.tex, git log for last edit date
   - Code: test coverage (covr for R, coverage.py for Python), lint count, last commit
   - Simulations: result file counts, failure detection, last run date
   - Literature: reference counts, pipeline manifest if present, last search date
   - Tasks: parse tasks.md for open/completed counts, check sessions/ for recency
4. For each metric, compute the delta against the previous digest.
5. Apply staleness thresholds. Generate alerts for any threshold breaches.
6. Write the structured metrics to digests/YYYY-MM-DD.json.
7. Generate a natural-language digest from the JSON following the standard template.
   - Omit sections for artifact types this project does not have.
   - Collapse healthy sections to one line.
   - Expand sections with alerts.
   - Include specific, actionable suggested actions.
8. Write the digest to digests/YYYY-MM-DD.md.
9. If a digest already exists for today's date, overwrite it (idempotent).
```

---

## Session Startup Integration (Step 5a)

The session startup protocol is extended with a health digest check as **Step 5a** (per P5-D5).

1. Check `digests/` for the most recent `.md` file.
2. If a digest exists and is **less than 7 days old**:
   - Read "Status at a Glance" and "Alerts" sections.
   - Present summary: "The most recent health digest (YYYY-MM-DD) shows: [overall status]. Alerts: [list]."
   - Mention: "Full digest available at digests/YYYY-MM-DD.md"
3. If a digest exists but is **more than 7 days old** or missing:
   - Note: "No recent health digest. Consider running one or scheduling via local task scheduler."
4. If **no digest exists**:
   - Note: "No health digests found for this project. Would you like me to generate one?"

---

## Digest vs. latest-summary.md

The digest and `memory/latest-summary.md` are **separate systems**.

| Dimension | `memory/latest-summary.md` | `digests/YYYY-MM-DD.md` |
|-----------|---------------------------|------------------------|
| Author | Session agent at close | Health monitor subagent |
| Content | Decisions, error knowledge, architectural state | Quantitative metrics, deltas, staleness alerts |
| Update trigger | Every session close | Scheduled (weekly) or on-demand |
| Curation | Manually compacted (P2-D1) | Machine-generated, never curated |
| Loaded at startup | Always (unconditional) | If recent (Step 5a) |

**The digest does NOT update `memory/latest-summary.md`.** If the digest reveals something that should be in project memory (e.g., "simulations are stalled"), that update happens during a human-attended session.

**Cross-reference, not merge.** The startup protocol reads both files. If both mention the same issue, the agent synthesizes them rather than presenting both verbatim.

---

## Staleness Detection

### Time-Based Staleness

Each artifact type has configurable warning and stale thresholds (see Staleness Threshold Summary). The data collection layer computes `days_since_*` values; threshold comparison generates alerts deterministically.

### Scope Creep Detection

1. Compute `net_task_delta` = current open tasks - previous digest open tasks.
2. Track `consecutive_positive_deltas` across digests by reading the sequence of `.json` files.
3. If `consecutive_positive_deltas >= 3`: generate a scope creep warning.

The alert is informational, not prescriptive: "Task count has grown for N consecutive digests -- is this intentional expansion or scope creep?"

### Optional: Stalled Branch Detection

```bash
git for-each-ref --sort=-committerdate \
  --format='%(refname:short) %(committerdate:iso)' refs/heads/ 2>/dev/null
```

Branches older than the configured threshold (default: 14 days) are flagged. Disabled by default; enabled via `health-config.yaml` `advanced.stalled_branch_detection`.

### Optional: Abandoned Task Detection

Open tasks in `tasks.md` with no associated git activity for longer than the task staleness threshold are flagged. Disabled by default (`advanced.abandoned_task_detection: false`) due to high false-positive rate for non-code tasks.
