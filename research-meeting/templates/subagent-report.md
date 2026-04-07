# Subagent Report Template

<!-- TOKEN BUDGET: Main agent consumption target is ~150-580 tokens regardless of depth tier. -->
<!-- Subagents MUST keep the rendered report within this budget so the orchestrator can ingest it in a single pass. -->

```yaml
---
task: "<string: short task description>"
status: "<completed | incomplete | blocked | failed>"
depth: "<light | deep>"
requested_by: "<string: identifier of the requesting agent>"
skill_used: "<string: skill name or 'none'>"
date: "<YYYY-MM-DD>"
context_files:
  - "<path/to/file>"
output_artifacts:
  - "<path/to/artifact>"
tags:
  - "<string>"
---
```

## Section Order and Budgets

Reports MUST include all six sections below, in order.
Each section has a token budget per depth tier.
Omit section content (write "N/A") only when genuinely not applicable, but always keep the heading.

| #  | Section                          | Light budget | Deep budget |
|----|----------------------------------|-------------|-------------|
| 1  | Executive Summary                | 30-60 tokens | 60-120 tokens |
| 2  | Key Findings                     | 40-80 tokens | 80-160 tokens |
| 3  | Methodology                      | 15-30 tokens | 40-80 tokens  |
| 4  | Artifacts                        | 20-40 tokens | 40-80 tokens  |
| 5  | Limitations and Open Questions   | 20-40 tokens | 40-80 tokens  |
| 6  | References                       | 10-20 tokens | 20-60 tokens  |
|    | **Total (approx)**               | **~150-270 tokens** | **~280-580 tokens** |

Both tiers stay within the ~150-580 token main-agent consumption window.

---

## Body Template

### Executive Summary

<!-- Light: 1-2 sentences. Deep: 2-4 sentences. -->
<!-- State what was done and the top-level result. -->

### Key Findings

<!-- Light: 2-3 bullet points. Deep: 3-6 bullet points. -->
<!-- Actionable findings the requesting agent needs. -->

### Methodology

<!-- Light: 1 sentence or bullet. Deep: 2-4 bullets describing approach, tools, and reasoning. -->

### Artifacts

<!-- Light: list paths only. Deep: list paths with one-line descriptions. -->
<!-- Reference output_artifacts from frontmatter. -->

### Limitations and Open Questions

<!-- Light: 1-2 bullets. Deep: 2-4 bullets. -->
<!-- Caveats, scope gaps, or unresolved questions for the caller. -->

### References

<!-- Light: list file paths or URLs consulted. Deep: annotated list with relevance notes. -->
