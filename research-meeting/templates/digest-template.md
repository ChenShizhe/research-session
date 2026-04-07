# Digest Output Format Template

This template defines the structure and format rules for the human-readable health digest (`digests/YYYY-MM-DD.md`). The LLM summarization layer renders the JSON intermediate into this format.

---

## Header

Every digest begins with a header block containing four required fields:

```markdown
# Health Digest: {{project_name}}

- **Generated:** {{generated_at}}  (e.g. 2026-04-03T09:00:00Z)
- **Period:** {{previous_digest_date}} to {{generated_date}}  (e.g. 2026-03-27 to 2026-04-03)
- **Digest #:** {{digest_number}}
```

Field sources (from JSON intermediate `meta`):
| Field | JSON Path |
|-------|-----------|
| `project_name` | `meta.project` |
| `generated_at` | `meta.generated_at` |
| `previous_digest_date` | `meta.previous_digest` (or "initial" if first run) |
| `generated_date` | date portion of `meta.generated_at` |
| `digest_number` | `meta.digest_number` |

If this is the first digest (`meta.previous_digest` is null), the Period line reads: **Period:** initial

---

## Status at a Glance

A summary table immediately after the header. Four required fields:

```markdown
## Status at a Glance

| Indicator              | Value              |
|------------------------|--------------------|
| **Overall Status**     | {{overall_status}} |
| **Days Since Last Session** | {{days_since_session}} |
| **Open Tasks**         | {{open}} / {{total}} ({{open_ratio}}%) |
| **Active Alerts**      | {{alert_count}}    |
```

### Overall Status values

Derived from the aggregated alert list using the protocol's status logic:

| Condition | Value |
|-----------|-------|
| 0 `[!]` alerts | **On Track** |
| 1-2 `[!]` alerts, none at "stale" severity | **Needs Attention** |
| 3+ `[!]` alerts, OR any "stale"-level threshold breached, OR no session in 30+ days | **Stalled** |

### Field sources

| Field | JSON Path |
|-------|-----------|
| `days_since_session` | `tasks.days_since_session` |
| `open` | `tasks.open` |
| `total` | `tasks.total` |
| `open_ratio` | computed: `round(open / total * 100)` |
| `alert_count` | count of all entries across every category's `alerts` array |

If the Tasks category is unavailable, `Days Since Last Session` and `Open Tasks` display "n/a".

---

## Per-Category Sections

One section per available category, in this order: **Manuscript**, **Code**, **Simulations**, **Literature**, **Tasks**. Each section follows the same three-part structure.

### Section structure

```markdown
## {{Category Name}}

{{current_values}}

{{deltas}}

{{alerts}}
```

### 1. Current Values

Present the category's key metrics as a table or short list. Use the appropriate metrics for each category:

**Manuscript:**
```markdown
| Metric | Value |
|--------|-------|
| Total word count | {{total_word_count}} |
| Section completion | {{completed_sections}} / {{total_sections}} |
| Days since last edit | {{days_since_edit}} |
```

**Code:**
```markdown
| Metric | Value |
|--------|-------|
| Language | {{language}} |
| Test coverage | {{test_coverage_percent}}% |
| Lint warnings | {{lint_warnings}} |
| Days since last commit | {{days_since_commit}} |
```

**Simulations:**
```markdown
| Metric | Value |
|--------|-------|
| Completed / planned | {{completed}} / {{planned}} |
| Failed jobs | {{failed}} |
| Days since last run | {{days_since_run}} |
```

**Literature:**
```markdown
| Metric | Value |
|--------|-------|
| Papers in collection | {{papers_in_collection}} |
| Vault coverage | {{vault_coverage}} |
| Days since last search | {{days_since_search}} |
```

**Tasks:**
```markdown
| Metric | Value |
|--------|-------|
| Open / total | {{open}} / {{total}} |
| Net task delta | {{net_delta}} |
| Consecutive positive deltas | {{consecutive_positive_deltas}} |
| Days since last session | {{days_since_session}} |
```

### 2. Deltas

Show change since the previous digest. Prefix positive values with `+`, negative with `-`. Use `--` when the delta is `null` (first digest).

```markdown
**Changes since last digest:**
- Word count: +{{delta.total_word_count}}
- Sections changed: {{delta.sections_changed | join(", ")}}
```

Format rules for deltas:
- Positive deltas that represent improvement (e.g., coverage up, word count up, lint warnings down): plain text.
- Negative deltas that represent regression (e.g., coverage down, lint warnings up): bold.
- Null deltas (first digest): display `--` with note "(first digest -- no deltas available)".

### 3. Alerts

List any `[!]` alerts from the category's `alerts` array. Each alert includes severity and message:

```markdown
[!] **{{severity}}:** {{message}}
    File: {{artifact}}
```

If the category has no alerts, this sub-section is omitted entirely (do not print "No alerts").

---

## Alerts (Aggregated)

After all per-category sections, an aggregated alerts section collects every alert across all categories in one place for quick scanning:

```markdown
## Alerts

{{#if no_alerts}}
No active alerts.
{{else}}
{{#each alert}}
- [!] **{{severity}}** ({{category}}): {{message}}
  {{#if artifact}}— See: `{{artifact}}`{{/if}}
{{/each}}
{{/if}}
```

Alert severity levels:
- **warning** — a threshold has been breached but has not reached the stale level.
- **stale** — the artifact has exceeded the stale threshold and needs immediate attention.

---

## Suggested Actions

Specific, actionable recommendations derived from the alerts and project state. Each action references a concrete file, task, or command.

```markdown
## Suggested Actions

{{#each action}}
- [ ] {{description}}
      {{#if file}}File: `{{file}}`{{/if}}
      {{#if task}}Task: {{task}}{{/if}}
      {{#if command}}Run: `{{command}}`{{/if}}
{{/each}}
```

### Action generation rules

1. Every alert should map to at least one suggested action.
2. Actions must be specific, not generic. Reference actual file paths, task descriptions, or commands.
3. Prioritize actions by severity: stale alerts before warning alerts.
4. Scope creep alerts suggest reviewing `tasks.md` and triaging open tasks.
5. Staleness alerts suggest the specific artifact type that needs attention (e.g., "Edit `manuscript/main.tex` -- Discussion section has 0 words").
6. Failed simulation alerts reference the specific error file (e.g., "Investigate `results/sim-042.err`").
7. If there are no alerts, this section reads: "No actions needed -- all metrics are healthy."

---

## Degraded Mode Notes

If any metric was unavailable due to missing tools or directories, append a notes section:

```markdown
## Notes

{{#each note}}
- {{message}}
{{/each}}
```

Examples:
- "Test coverage metric unavailable (covr not installed)."
- "Simulations section omitted (no `results/` directory)."
- "First digest for this project -- no deltas available."

If there are no degraded-mode notes, this section is omitted.

---

## Format Rules

These rules govern how the LLM renders the digest from JSON. They control section visibility and verbosity.

### Rule 1: Omit irrelevant sections

If a category has `available: false` in the JSON intermediate, **omit the entire section**. Do not render a placeholder, "N/A" row, or empty table. The digest should only contain sections for artifact types the project actually has.

### Rule 2: Collapse healthy sections

If a category has **zero alerts** and **no significant deltas** (all deltas are zero, null, or within normal range), collapse the section to a single summary line:

```markdown
## Manuscript

On track. 8,432 words across 4 sections. Last edit: 2 days ago.
```

A "significant delta" is any non-zero change in a key metric. The threshold for significance is left to the LLM's judgment based on the metric type (e.g., a word count change of +5 may not be significant, but +500 is).

### Rule 3: Expand sections with alerts

If a category has **one or more alerts**, render the full section structure: current values table, deltas, and each alert with its detail. Do not collapse.

### Rule 4: Delta formatting

- Always show deltas as `current_value (delta)` — e.g., "87.3% (+2.1%)" or "4 warnings (-3)".
- Use `+` prefix for increases, `-` prefix for decreases, `--` for null (no previous digest).
- Bold negative trends (values moving in the wrong direction).

### Rule 5: Alert marker consistency

All alerts use the `[!]` prefix marker for visual scanning. The marker appears both in per-category sections and in the aggregated Alerts section.

### Rule 6: Digest length

The digest length correlates with the number of issues, not the number of metrics. A healthy project produces a short digest (header + status at a glance + collapsed sections + "no actions needed"). A project with multiple alerts produces a longer digest with expanded sections and specific actions.
