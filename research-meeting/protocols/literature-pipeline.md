# Literature Review Pipeline Orchestration Protocol

## Purpose

Orchestrate the automated literature review pipeline as a structured delegation chain. The pipeline chains five stages — each a one-shot subagent delegation per P3-D1 — coordinated through a shared manifest. The manifest is the pipeline's state. Human-in-the-loop checkpoints are mandatory between key stages.

This protocol is the operational counterpart to the P5-D1 design specification. It tells the group lead (or main agent) **how** to run the pipeline, stage by stage.

---

## 1. Architecture Overview

### 1.1 Pipeline as Structured Delegation Chain

The pipeline is **not** a standalone orchestrator. It is a coordinated sequence of one-shot subagent delegations (P3-D1 pattern) where:

- Each stage reads from and writes to a shared **pipeline manifest** (`pipeline/manifest.json`).
- The **group lead** (or main agent in single-agent sessions) decides when to run each stage, spawns subagents, and presents checkpoints.
- Human judgment is required at three mandatory checkpoints. The pipeline automates mechanical work; it does not automate intellectual decisions.

### 1.2 Five-Stage Flow

```
[1. Watcher]  -->  [2. Screener]  -->  [3. Extractor]  -->  [4. Synthesizer]  -->  [5. Presenter]
     |                  |                    |                     |                      |
paper-discovery    LLM screening        paper-reader       research-synthesizer    in-session summary
                   (pipeline stage)                                                + knowledge-maester
     |                  |                    |                     |                      |
 manifest.json     manifest.json       extraction files      synthesis.md           vault notes +
 (candidates)      (screened)           + manifest update     + gap analysis         session briefing
```

### 1.3 Manifest-Driven Data Flow

The pipeline manifest (`pipeline/manifest.json`) is the single source of truth for pipeline state. Every paper that enters the pipeline gets a manifest entry. Every stage reads the manifest, processes papers at the appropriate status, and updates the manifest.

Paper statuses flow through: `discovered` -> `screened-in` | `screened-out` | `needs-human-review` -> `extracted` | `extraction-failed` | `inaccessible` -> `synthesized`.

### 1.4 Pipeline Artifact Location

```
~/Documents/Research/<project-name>/
  pipeline/
    manifest.json              # pipeline state (single source of truth)
    config.yaml                # pipeline configuration
    screening-log.md           # audit trail of screening decisions
    synthesis/
      latest-synthesis.md      # most recent cross-paper synthesis
      gap-analysis.md          # identified research gaps
    checkpoints/
      YYYY-MM-DD-screening-review.md
      YYYY-MM-DD-extraction-review.md
      YYYY-MM-DD-synthesis-review.md
  subagent-outputs/            # per P3-D1 output location
```

---

## 2. Stage Definitions and Delegation Profiles

### 2.1 Stage 1: Watcher (Discovery)

**Purpose:** Find candidate papers matching the project's research scope.

**Skill used:** paper-discovery

**Trigger:** On-demand (user or group lead requests a literature search) or scheduled (living review mode).

**Input:**
- `pipeline/config.yaml` — keywords, sources, inclusion/exclusion criteria
- `pipeline/manifest.json` — existing papers (for deduplication)
- `references/` — existing project references (for deduplication)

**Process:**
1. Subagent loads paper-discovery skill.
2. Searches configured sources (Zotero library, arXiv, OpenAlex, optionally PubMed, Semantic Scholar).
3. Deduplicates against existing manifest entries and project references.
4. Checks citadel vault (P3-D2 traversal) for papers already in the vault.
5. Verifies DOIs via CrossRef API (see Section 5.2).
6. Writes discovery report to `subagent-outputs/`.
7. Updates manifest: new entries added with `status: discovered`.

**Output:**
- Updated `pipeline/manifest.json` with new candidate entries
- Discovery report in `subagent-outputs/`

**Delegation Profile:**

| Field | Value |
|-------|-------|
| Depth | Light (keyword search) or Deep (comprehensive survey) |
| Mode | Background |
| Model | Sonnet-tier (standard reasoning) |
| Max turns | 30 |

---

### 2.2 Stage 2: Screener (Filtering and Prioritization)

**Purpose:** Evaluate each discovered paper against inclusion/exclusion criteria. Rank by relevance. Filter out irrelevant papers.

**Skill used:** None (pipeline-specific LLM screening stage).

**Trigger:** After Watcher completes and user has reviewed discovery results, or manually on unscreened manifest entries. If the user has no feedback, screening proceeds automatically using LLM reasoning.

**Input:**
- `pipeline/manifest.json` — papers with `status: discovered`
- `pipeline/config.yaml` — inclusion/exclusion criteria (may be minimal on first run)
- `domain-prior.md` — project context for relevance assessment
- User feedback (optional) — informal notes on relevance

**Process:**
1. Subagent reads unscreened papers from manifest.
2. **If explicit criteria exist in config.yaml:** Evaluate each paper using the QA-framework screening protocol (Section 3).
3. **If no explicit criteria exist (early runs):** Screen based on relevance to the research question in `domain-prior.md`, plus any user feedback from discovery review.
4. Papers receiving "include" on all mandatory criteria (or judged relevant by LLM reasoning) are marked `status: screened-in`.
5. Papers failing any mandatory criterion (or judged irrelevant) are marked `status: screened-out` with reason.
6. Included papers are ranked by composite relevance score.
7. Screening decisions are logged to `pipeline/screening-log.md`.

**Output:**
- Updated `pipeline/manifest.json` with screening decisions, confidence scores, and criterion-level scores
- Updated `pipeline/screening-log.md` with decision audit trail
- **CHECKPOINT 1** written to `pipeline/checkpoints/` (see Section 4.1)

**Delegation Profile:**

| Field | Value |
|-------|-------|
| Depth | Light (per-paper, bounded) |
| Mode | Background (batch screening) |
| Model | Sonnet-tier (judgment without deep reasoning) |
| Max turns | 20 + 2 per paper |

---

### 2.3 Stage 3: Extractor (Deep Reading)

**Purpose:** Perform deep structured reading of each included paper. Extract claims, methods, findings, and relevance assessment.

**Skill used:** paper-reader

**Trigger:** After screening checkpoint (Section 4.1) is approved by user, or on individual papers on-demand.

**Input:**
- `pipeline/manifest.json` — papers with `status: screened-in`
- Per-paper: PDF, citadel note, or web-accessible text
- `domain-prior.md` — project context for relevance framing

**Process:**
1. For each screened-in paper (priority-ordered by relevance score, highest first):
   a. **Citadel pre-check:** Check if the paper already has a comprehensive vault note. If so, use the vault note as primary source and only extract missing sections.
   b. Spawn paper-reader subagent with delegation brief (per P3-D1 protocol).
   c. Subagent performs deep structured extraction: section-by-section comprehension, claim extraction, methodology analysis.
   d. Output written to `subagent-outputs/` (per P3-D1 output format).
   e. Update manifest: `status: extracted`, link to output file.
2. Optionally, spawn knowledge-maester subagent to write/update vault note for each extracted paper.

**Batch processing:** Papers are processed sequentially by relevance score. In multi-agent sessions (Phase 4), the literature specialist can delegate multiple paper-reader subagents in parallel.

**Output:**
- Extraction reports in `subagent-outputs/` (one per paper)
- Updated vault notes in citadel (via knowledge-maester, optional)
- Updated `pipeline/manifest.json` with extraction status and file links
- **CHECKPOINT 2** written to `pipeline/checkpoints/` (see Section 4.2)

**Delegation Profile:**

| Field | Value |
|-------|-------|
| Depth | Deep (full paper reading) |
| Mode | Background |
| Model | Sonnet-tier or Opus-tier (comprehension quality is critical) |
| Max turns | 40 per paper |

---

### 2.4 Stage 4: Synthesizer (Cross-Paper Analysis)

**Purpose:** Produce cross-paper synthesis from individual extractions. Identify themes, conflicts, gaps, and the project's position relative to existing work.

**Skill used:** research-synthesizer

> **Note:** research-synthesizer may need revision for pipeline-triggered synthesis. The input/output contract is specified here so that it works with whatever synthesis capability exists at runtime.

**Trigger:** After extraction checkpoint (Section 4.2) is approved, or on-demand when the user wants a synthesis update.

**Input:**
- Extraction reports from Stage 3 (executive summaries + key findings)
- `pipeline/manifest.json` — extracted papers with metadata
- `domain-prior.md` — central research question for relevance anchoring
- `memory/latest-summary.md` — current project state for positioning

**Process:**
1. Subagent loads research-synthesizer skill.
2. Reads executive summaries from all extracted papers (progressive disclosure — full reports only if needed).
3. Performs multi-pass synthesis:
   a. **Claim extraction pass:** Identify key claims, methods, and findings across papers.
   b. **Thematic clustering:** Group related claims into thematic clusters.
   c. **Conflict identification:** Flag papers that make contradictory claims or use incompatible assumptions.
   d. **Gap analysis:** Identify what the collected literature does NOT address that is relevant to the project's research question. Use structured gap detection: explicit gaps from paper text + implicit gaps inferred from missing coverage areas.
   e. **Positioning:** Summarize where the project's current work fits relative to the synthesized literature.
4. Each synthesis claim carries a confidence score (0.0-1.0) per Section 5.3.
5. Write synthesis to `pipeline/synthesis/latest-synthesis.md`.
6. Write gap analysis to `pipeline/synthesis/gap-analysis.md`.

**Output:**
- `pipeline/synthesis/latest-synthesis.md` — structured cross-paper synthesis
- `pipeline/synthesis/gap-analysis.md` — identified gaps and open questions
- **CHECKPOINT 3** written to `pipeline/checkpoints/` (see Section 4.3)

**Delegation Profile:**

| Field | Value |
|-------|-------|
| Depth | Deep (cross-paper reasoning) |
| Mode | Background |
| Model | Opus-tier (synthesis quality is critical — cross-paper reasoning is the hardest task) |
| Max turns | 50 |

---

### 2.5 Stage 5: Presenter (In-Session Summary and Vault Integration)

**Purpose:** Make pipeline results accessible within the session. Update the citadel vault. Brief the user.

**Skill used:** knowledge-maester (for vault writes); no skill for session briefing.

**Trigger:** At session start (auto-present latest pipeline results), or on-demand when pipeline completes.

**Input:**
- `pipeline/synthesis/latest-synthesis.md`
- `pipeline/synthesis/gap-analysis.md`
- `pipeline/manifest.json` — pipeline statistics

**Process:**
1. **Session briefing:** The group lead reads the synthesis executive summary and presents a concise briefing:
   - Papers discovered, screened, extracted since last session.
   - Top 3-5 findings from the synthesis.
   - Key gaps identified.
   - Recommended discussion topics based on findings.
2. **Vault integration:** Spawn knowledge-maester subagent to write/update a literature review MOC (Map of Content) note in the citadel vault. Cross-link individual paper notes and update relevant topic notes.
3. **Specialist briefing (multi-agent sessions):** The literature specialist reads the full synthesis and gap analysis as part of its context, making it immediately informed about the literature landscape.

**Output:**
- In-session briefing (conversational, not a file)
- Updated citadel vault notes (via knowledge-maester)

**Delegation Profile:**

| Field | Value |
|-------|-------|
| Depth | Light (vault writes) |
| Mode | Foreground (session briefing is immediate) |
| Model | Sonnet-tier (for vault writes) |
| Max turns | 20 |

---

## 3. QA-Framework Screening Protocol

### 3.1 Screening Approach

The screening protocol uses a question-answering framework rather than a single binary classification. Each inclusion/exclusion criterion is framed as a yes/no question that the LLM answers with a confidence score.

This provides:
- **Criterion-level transparency:** The user can see exactly which criterion caused an exclusion.
- **Structured audit trail:** Every decision is traceable.
- **Tunable sensitivity:** Individual criteria can be made stricter or more lenient.

### 3.2 Criterion Format

Criteria are defined in `pipeline/config.yaml`:

```yaml
inclusion_criteria:
  - question: "Does the paper address estimation or inference for point processes?"
    mandatory: true
    weight: 1.0
  - question: "Does the paper involve kernel smoothing, bandwidth selection, or nonparametric estimation?"
    mandatory: false
    weight: 0.8

exclusion_criteria:
  - question: "Is this exclusively about spatial point processes with no temporal component?"
    action: exclude
  - question: "Is this a review/survey paper with no original methodology?"
    action: flag_as_survey
```

**Mandatory criteria:** A paper must pass all mandatory criteria to be included. Failing any mandatory criterion results in `status: screened-out`.

**Weighted criteria:** Non-mandatory criteria contribute to the composite relevance score. A paper's relevance score is the weighted average of its non-mandatory criterion confidence scores.

**Exclusion criteria:** If an exclusion criterion is triggered, the paper is excluded regardless of inclusion scores.

### 3.3 Per-Paper Screening Output

For each paper, the screener records:

```json
{
  "decision": "include | exclude | needs-human-review",
  "confidence": 0.85,
  "criteria_scores": {
    "criterion_1_question": { "answer": "yes", "confidence": 0.92 },
    "criterion_2_question": { "answer": "no", "confidence": 0.45 }
  },
  "reasoning": "Brief explanation of the overall decision.",
  "screened_by": "<model identifier>",
  "screened_at": "ISO-8601 timestamp"
}
```

Papers with confidence < 0.7 on any mandatory criterion are marked `needs-human-review` rather than auto-decided.

### 3.4 Criteria Evolution Pattern

Screening criteria are NOT expected to be well-defined before the first discovery run. They evolve through use:

1. **First run (no criteria):** The Watcher discovers papers broadly. The group lead presents titles, authors, and abstracts to the user. The LLM screens based on its reasoning about the project's research question (from `domain-prior.md`), without explicit criteria.

2. **User feedback round:** The user reviews the screening results and provides informal feedback (e.g., "This one looks relevant because it addresses kernel bandwidth" or "Skip these — they're spatial-only"). The group lead translates this feedback into candidate criteria and proposes them for `config.yaml`.

3. **Criteria refinement:** After 2-3 rounds of discovery + feedback, the criteria in `config.yaml` stabilize. They may continue to evolve as the project's scope sharpens.

4. **Ongoing tuning:** The group lead monitors screening accuracy at each checkpoint. If borderline papers are consistently misjudged, the group lead proposes criterion adjustments.

This approach avoids the cold-start problem of defining criteria from thin air before seeing any papers. The group lead should offer concrete options for the user to accept/reject rather than asking the user to define criteria from scratch.

### 3.5 Screening Audit Trail

Every screening decision is appended to `pipeline/screening-log.md`:

```markdown
## Screening Run: YYYY-MM-DD

Papers screened: N
Included: X | Excluded: Y | Needs human review: Z

### Included
| Paper | Confidence | Key criteria met |
|-------|-----------|-----------------|
| <cite_key> | 0.92 | relevance, methods |

### Excluded
| Paper | Confidence | Reason |
|-------|-----------|--------|
| <cite_key> | 0.35 | Failed mandatory criterion: "Does the paper address..." |

### Needs Human Review
| Paper | Confidence | Ambiguity |
|-------|-----------|-----------|
| <cite_key> | 0.65 | Borderline on methods criterion (0.55) |
```

---

## 4. Human-in-the-Loop Checkpoints

Three mandatory checkpoints interrupt the pipeline for human review. The pipeline does **not** proceed past a checkpoint without explicit user approval. Each checkpoint produces a review file in `pipeline/checkpoints/`.

### 4.1 Checkpoint 1: Post-Screening Review

**When:** After Stage 2 (Screener) completes.

**Group lead presents:**
- Number of papers discovered, included, excluded.
- A sample of included papers with relevance scores and criterion-level decisions.
- A sample of excluded papers (especially those near the threshold) for verification.
- All papers flagged as `needs-human-review`.

**User actions:**
- **Approve:** Proceed to Stage 3 (Extraction).
- **Adjust criteria:** Modify criteria in `config.yaml` and re-screen.
- **Override:** Manually flip individual include/exclude decisions.

**Checkpoint file:** `pipeline/checkpoints/YYYY-MM-DD-screening-review.md`

### 4.2 Checkpoint 2: Post-Extraction Spot-Check

**When:** After Stage 3 (Extractor) completes a batch.

**Group lead presents:**
- Executive summaries from extracted papers.
- A randomly selected extraction for the user to verify against the source paper (spot-check for accuracy).
- Any papers marked `extraction-failed` or `inaccessible`.

**User actions:**
- **Approve:** Proceed to Stage 4 (Synthesis).
- **Re-extract:** Request re-extraction of specific papers.
- **Flag quality issues:** Report extraction errors for the group lead to address.

**Checkpoint file:** `pipeline/checkpoints/YYYY-MM-DD-extraction-review.md`

### 4.3 Checkpoint 3: Post-Synthesis Review

**When:** After Stage 4 (Synthesizer) completes.

This is the most important checkpoint — the synthesis is the pipeline's primary intellectual output.

**Group lead presents:**
- Full synthesis (`pipeline/synthesis/latest-synthesis.md`).
- Gap analysis (`pipeline/synthesis/gap-analysis.md`).
- Confidence flags on claims with thin or conflicting evidence.

**User reviews:**
- Thematic clusters for coherence.
- Cross-paper conflict identification for accuracy.
- Gap analysis for completeness.
- Positioning statement for correctness.

**User actions:**
- **Approve:** Proceed to Stage 5 (Presenter / vault integration).
- **Request revisions:** Re-run synthesis with guidance.
- **Add observations:** Manually supplement the synthesis.

**Checkpoint file:** `pipeline/checkpoints/YYYY-MM-DD-synthesis-review.md`

---

## 5. Quality Assurance

### 5.1 Citation Grounding Rule

**Every claim in pipeline output must be traceable to a specific source.**

| Output type | Grounding requirement |
|-------------|----------------------|
| Extraction reports | Every claim must reference a specific section, theorem, or page of the source paper. |
| Synthesis | Every cross-paper claim must reference the extraction reports it draws from. |
| Gap analysis | Every gap must reference the papers or thematic clusters that define its boundaries. |

**Enforcement mechanisms:**

1. **Delegation brief instructions:** All subagent delegation briefs include: "Every claim must cite a specific source. Do not generate unsupported claims."
2. **Output format requirements:** The subagent report template (P3-D1) requires a References section. Synthesis and gap analysis formats require per-claim attribution.
3. **Checkpoint review:** Human spot-checks claims against source papers at the extraction and synthesis checkpoints.

Unsourced claims in any pipeline output are treated as defects. The group lead flags them at checkpoint review and requests correction before proceeding.

### 5.2 DOI Verification

Before any paper enters the pipeline manifest, its DOI (if provided) is verified via **CrossRef API** resolution.

**Process:**
1. During Stage 1 (Watcher), the subagent resolves each DOI against the CrossRef API (`https://api.crossref.org/works/<doi>`).
2. A successful resolution confirms the DOI maps to a real publication. The manifest records `doi_verified: true`.
3. A failed resolution (404 or mismatch) sets `doi_verified: false`. The paper is flagged in the discovery report for manual verification.
4. If web access is unavailable during the Watcher run, the paper is accepted with `doi_verified: unverified` and flagged for later verification.

**Why this matters:** Fabricated DOIs in LLM-generated content are a documented hallucination risk. DOI verification is a lightweight check that catches the most obvious fabrications.

### 5.3 Confidence Scoring

Each screening decision and synthesis claim carries a confidence score on a 0.0-1.0 scale.

**Screening confidence:**
- Each criterion answer has a confidence score (0.0-1.0).
- The overall screening decision has a composite confidence score (weighted average of criterion-level scores).
- Papers with composite confidence < 0.7 are marked `needs-human-review` rather than auto-decided.
- Papers with confidence >= 0.7 are auto-decided but still subject to checkpoint review.

**Synthesis confidence:**
- Each claim in the synthesis carries an evidence strength indicator:
  - **High confidence (0.8-1.0):** Multiple concordant sources support the claim.
  - **Medium confidence (0.5-0.79):** Limited sources or minor disagreements.
  - **Low confidence (< 0.5):** Single source, conflicting evidence, or inference from indirect evidence.
- Low-confidence claims are flagged prominently in the synthesis output with an uncertainty marker.

**Calibration note:** These scores are heuristic, not calibrated probabilities. Their purpose is to direct human attention to the items most likely to need review. They are not suitable for automated decision thresholds beyond the screening `needs-human-review` flag.

---

## 6. Orchestration Flow

### 6.1 How the Group Lead Runs the Pipeline

```
User: "Let's update the literature review"
  |
  v
Group Lead reads pipeline/manifest.json
  |
  v
Group Lead determines which stages need to run:
  - No recent Watcher run?           --> trigger Stage 1
  - Unscreened papers in manifest?    --> trigger Stage 2
  - Screened-in papers unextracted?   --> trigger Stage 3
  - Extractions updated since last synthesis? --> trigger Stage 4
  - Results ready to present?         --> Stage 5
  |
  v
Group Lead spawns one-shot subagents for each needed stage (P3-D1 protocol)
  |
  v
Between stages: mandatory human review at checkpoints (Section 4)
  |
  v
Group Lead presents results to user (Stage 5)
```

### 6.2 Stage Sequencing Rules

- Stages run sequentially (1 -> 2 -> 3 -> 4 -> 5). No stage may be skipped.
- The pipeline can **resume** from any stage. The group lead reads the manifest to determine which stages have already completed and starts from the next needed stage.
- Individual papers can be fast-tracked through stages (e.g., user requests immediate extraction of a specific paper without waiting for a full screening batch).
- The user can trigger any stage on-demand (e.g., "re-run synthesis with the new extractions").

### 6.3 Single-Agent vs. Multi-Agent Orchestration

| Context | Orchestrator | How it works |
|---------|-------------|-------------|
| Single-agent session | Main agent | Main agent spawns subagents for each stage sequentially. |
| Multi-agent session | Group lead | Group lead delegates to literature specialist, which manages execution and further delegates to subagents. |
| Scheduled (living review) | Scheduled task | Task runs Watcher stage autonomously; results wait for next session. |

---

## 7. Error Handling

All error handling follows the P3-D1 **fail-loud** principle: failures are reported immediately and prominently. There is no automatic retry. The user decides whether to retry, re-scope, or handle inline.

### 7.1 Error Table

| Error Type | Stage | Handling | Manifest Status |
|------------|-------|----------|-----------------|
| **Source unavailable** (arXiv down, Zotero timeout) | Watcher | Log the failure. Proceed with available sources. Report which sources failed in the discovery report. | N/A (no paper entry created) |
| **Paper not accessible** (no PDF, paywalled) | Extractor | Mark paper in manifest. Report in extraction output. Do not block other papers. Remind user to download manually. | `inaccessible` |
| **Screening ambiguity** (confidence < 0.7 on mandatory criterion) | Screener | Mark paper for human decision. Surface prominently at Checkpoint 1. | `needs-human-review` |
| **Extraction failure** (subagent error, timeout, corrupt PDF) | Extractor | Mark paper in manifest. Log error details. Do not retry automatically. | `extraction-failed` |
| **Synthesis failure** (subagent error, insufficient extractions) | Synthesizer | Report what failed. Produce partial synthesis from available extractions if possible. Surface at Checkpoint 3. | N/A (synthesis-level, not per-paper) |
| **DOI unresolvable** | Watcher | Accept paper with `doi_verified: false`. Flag in discovery report. | `discovered` (with `doi_verified: false`) |
| **Vault write failure** (knowledge-maester error) | Presenter | Report failure. Pipeline results remain in `pipeline/` directory. Vault integration can be retried independently. | N/A |

### 7.2 Fail-Loud Reporting

When any stage encounters an error:

1. The error is logged in the subagent output file (per P3-D1 output format, `status: partial` or `status: failed`).
2. The manifest is updated to reflect the error state.
3. The group lead reports the error to the user at the next checkpoint or immediately if the error is blocking.
4. **No silent fallbacks.** If a source is unavailable, the user is told which source failed — the pipeline does not silently produce results from a subset of sources without disclosure.

### 7.3 Recovery

- **Retry a stage:** The user says "retry extraction for paper X." The group lead spawns a new subagent for that paper.
- **Skip a paper:** The user says "skip this paper." The group lead updates the manifest to `status: skipped`.
- **Resume the pipeline:** After fixing an issue (e.g., downloading a paywalled PDF), the user says "continue the pipeline." The group lead reads the manifest and picks up from the next needed stage.

---

## 8. Interaction with Other Protocols

| Protocol / Design | Interaction |
|-------------------|------------|
| P3-D1 (Delegation protocol) | Pipeline stages are delegated as one-shot subagents following the existing protocol. Output format unchanged. |
| P3-D2 (Citadel traversal) | Watcher and Extractor stages check the vault before external operations (deduplication, existing note detection). |
| P3-D3 (Skill integration) | paper-discovery, paper-reader, and knowledge-maester delegation profiles apply unchanged. Pipeline adds orchestration on top. |
| P4-D1 (Multi-agent architecture) | Literature specialist can own pipeline stages 1-4 in multi-agent sessions. Group lead triggers; specialist executes. |
| P4-D2 (Specialist roles) | Literature specialist role definition should note pipeline awareness. |
| P5-D2 (Living review) | Extends Watcher stage with scheduled mode, delta queries, discovery queue. See Section 9. |
| P5-D3 (Health digest) | Digest includes pipeline status (papers discovered, extracted, synthesis recency). |
| P5-D5 (Protocol amendments) | Session startup protocol extended to present latest pipeline results. |

---

## 9. Living Review (P5-D2)

The living review extends the pipeline's Watcher stage to run on a schedule, unattended, between interactive sessions. Its purpose is to keep the literature landscape current without requiring the user to manually trigger discovery runs.

### 9.1 Scheduled Watcher Mode

In scheduled mode the Watcher runs **unattended** with the following constraints:

- **Delta queries only.** The Watcher queries each source for papers published or updated since the last run (per-source timestamps in the manifest). It does not perform full-scope searches.
- **Discovery queue output.** Results are written to `pipeline/discovery-queue.md` (see Section 9.3), **not** directly to the manifest. This prevents untriaged candidates from entering the pipeline without human review.
- **No downstream stages.** The scheduled Watcher does not trigger screening, extraction, or synthesis. Those stages require human checkpoints and run only in interactive sessions.
- **Fail-safe.** If a source is unreachable, the Watcher logs the failure in the discovery queue run header and proceeds with remaining sources. The per-source timestamp for the failed source is **not** advanced, so the next run will retry that source's time window.

**Scheduling mechanism:** The scheduled Watcher is triggered by a local scheduled task (e.g., cron, launchd, Task Scheduler) or an external scheduler — not cloud-hosted tasks. Configuration is in `pipeline/config.yaml` under `living_review.schedule`.

**Delegation profile (scheduled mode):**

| Field | Value |
|-------|-------|
| Depth | Light (delta queries only) |
| Mode | Background (unattended) |
| Model | Sonnet-tier (standard reasoning sufficient for discovery) |
| Max turns | 20 |
| Human interaction | None — fully autonomous within Watcher scope |

### 9.2 Timestamp-Based Delta Queries

Each source maintains an independent `last_watcher_run` timestamp in the pipeline manifest (`pipeline/manifest.json` → `last_watcher_run.<source>`). The Watcher uses this timestamp to construct source-specific delta queries.

| Source | Delta Query Strategy | Timestamp Field |
|--------|---------------------|-----------------|
| **arXiv** | OAI-PMH `from` parameter or RSS feed filtered by `submittedDate` since last run. | `last_watcher_run.arxiv` |
| **OpenAlex** | `from_publication_date` filter on the Works API, set to the day after the last run. | `last_watcher_run.openalex` |
| **Zotero** | `since` parameter on the Zotero API (library version number or `dateModified` filter). | `last_watcher_run.zotero` |
| **PubMed** | `mindate` / `maxdate` parameters on the E-utilities search API, set to the window since last run. | `last_watcher_run.pubmed` |
| **Web search** | Fetch configured target URLs (from `living_review.web_search_targets` in config) and diff against previously seen content. No native delta API — relies on content comparison. | `last_watcher_run.web_search` |

**First run:** When `last_watcher_run.<source>` is `null`, the Watcher performs a full initial query (not delta) for that source. Subsequent runs use delta queries.

**Timestamp update rule:** A source's timestamp is updated only after a successful query. If the query fails, the timestamp is left unchanged so the next run retries the same window.

### 9.3 Discovery Queue Format

The discovery queue lives at `pipeline/discovery-queue.md`. Its format is specified in that file. Key design decisions:

- **Markdown, not JSON.** The queue is optimized for human readability at session start.
- **Append-only during Watcher runs.** The Watcher only appends; it never modifies or deletes existing entries.
- **Consumed at session start.** The group lead reads the queue and presents a summary. Entries are triaged (accept → manifest, reject → remove, defer → keep) during the interactive session.
- **Staleness cutoff.** Entries older than `living_review.max_age_days` (default 30) are deprioritized.

Each queue entry includes: title, authors, source, source-specific ID, DOI (with verification status), abstract snippet, delta type, discovery timestamp, and manifest status (`pending-triage`).

### 9.4 Manifest Diffing

When the Watcher processes delta query results, it compares each candidate against the current manifest to classify it:

| Delta Type | Condition | Action |
|------------|-----------|--------|
| **new** | No manifest entry with a matching DOI, source ID, or title. | Write to discovery queue as `delta type: new`. |
| **updated** | A manifest entry exists but source metadata has changed (e.g., new version on arXiv, updated abstract, added DOI). | Write to discovery queue as `delta type: updated`. Include a note describing what changed. |
| **retracted** | Source reports a retraction notice for a paper already in the manifest. | Write to discovery queue as `delta type: retracted`. Flag prominently — retractions affect synthesis validity. |

**Deduplication:** The Watcher deduplicates across sources using DOI (primary key), title similarity (fuzzy match fallback), and source-native IDs. A paper found by multiple sources in the same run produces a single queue entry listing all sources.

**Retraction handling:** Retracted papers that have already been synthesized trigger a mandatory re-synthesis flag. See Section 9.6.

### 9.5 Alert Mechanisms

Alerts notify the user that the living review has produced results requiring attention.

#### Session-Start Alert (Default)

At the start of every interactive session, the group lead checks `pipeline/discovery-queue.md`:

- If the queue contains entries, the group lead presents a summary:
  - Number of new, updated, and retracted candidates since the last session.
  - Top candidates by recency and source diversity.
  - Any retraction notices (highlighted prominently).
- If the queue is empty, no alert is shown.
- The alert fires when the number of pending entries meets or exceeds `living_review.alert_threshold` (default 3 in `pipeline/config.yaml`). Below that threshold, the group lead mentions the queue briefly but does not interrupt the session flow.

This is the default and requires no external setup.

#### Optional: Slack Notification

For teams using Slack, an optional webhook can post a summary to a configured channel when the scheduled Watcher completes with new candidates.

**Setup:** Add the webhook URL to `pipeline/config.yaml` under `living_review.alerts.slack_webhook`. The Watcher posts a message containing: run date, number of new candidates, and a one-line note to check the discovery queue at the next session.

**Not a replacement for session-start alerts.** Slack notifications are a convenience heads-up. The authoritative triage still happens at session start.

#### Optional: GitHub Issue

For projects tracked on GitHub, the Watcher can open an issue when it finds candidates above the alert threshold.

**Setup:** Add the repository and label to `pipeline/config.yaml` under `living_review.alerts.github_issue`. The Watcher creates an issue with: run date, candidate count, and a summary table of new entries.

**Auto-close:** The group lead closes the issue after triage at session start.

### 9.6 Incremental vs. Full Re-Synthesis Triggers

Not every discovery run requires a new synthesis. The pipeline distinguishes between incremental updates (add new papers to the existing synthesis) and full re-synthesis (rebuild the synthesis from scratch).

#### Incremental Synthesis

An incremental synthesis is triggered when **all** of the following are true:

- New papers have been extracted since the last synthesis.
- No retracted papers are present in the current synthesis.
- The number of newly extracted papers is ≤ 30% of the total papers in the synthesis.
- The existing synthesis is less than 90 days old.

In incremental mode, the Synthesizer:
1. Reads the existing synthesis (`pipeline/synthesis/latest-synthesis.md`).
2. Reads only the newly extracted papers.
3. Integrates new findings into the existing thematic structure.
4. Updates the gap analysis based on what the new papers address.
5. Marks the synthesis as "incrementally updated" with a list of papers added.

#### Full Re-Synthesis

A full re-synthesis is triggered when **any** of the following are true:

- A retracted paper is part of the current synthesis (retraction invalidates claims that may depend on it).
- The number of newly extracted papers exceeds 30% of the total papers in the synthesis.
- The existing synthesis is older than 90 days.
- The user explicitly requests a full re-synthesis.
- The project's research question has changed significantly (detected by comparing the current `domain-prior.md` against the research question recorded in the last synthesis).

In full re-synthesis mode, the Synthesizer rebuilds the entire synthesis from all extracted papers, as described in Section 2.4.

#### Trigger Evaluation

The group lead evaluates these triggers at the start of Stage 4 (Synthesis). The decision is logged in the synthesis checkpoint file:

```markdown
## Synthesis Trigger Evaluation

- Papers in current synthesis: N
- Newly extracted since last synthesis: M
- Ratio: M/N = X%
- Synthesis age: Y days
- Retracted papers in synthesis: [list or "none"]
- Research question changed: yes/no
- **Decision: incremental | full**
- **Reason:** <why this mode was chosen>
```

### 9.7 Scheduled Task Prompt Template

The following template is used by the scheduling mechanism (local scheduled task or external scheduler) to invoke the Watcher in scheduled mode. It is **model-agnostic** — it works with any LLM that can execute the pipeline protocol.

```
You are running a scheduled living review Watcher for the project at:
  {project_path}

Your task:
1. Read the pipeline configuration at {project_path}/pipeline/config.yaml.
2. Read the pipeline manifest at {project_path}/pipeline/manifest.json.
3. For each source listed under living_review.sources in the config:
   a. Read the source's last_watcher_run timestamp from the manifest.
   b. Query the source for papers published or updated since that timestamp.
      - If the timestamp is null, perform an initial full query for that source.
   c. Deduplicate results against the manifest (by DOI, title similarity, source ID).
   d. Verify DOIs via CrossRef API resolution.
   e. Classify each result as new, updated, or retracted (see protocol Section 9.4).
4. If web_search_targets are configured, fetch each URL and compare against
   previously seen content to identify new papers.
5. Append all results to {project_path}/pipeline/discovery-queue.md using the
   format specified in that file.
6. Update per-source last_watcher_run timestamps in the manifest for sources
   that were queried successfully. Do NOT update timestamps for failed sources.
7. If alerts are configured (slack_webhook or github_issue in config), send
   a notification summarizing the run.

Constraints:
- Do NOT modify the manifest's papers array. Only update last_watcher_run timestamps.
- Do NOT trigger screening, extraction, or synthesis stages.
- Do NOT require human interaction. If a source fails, log the failure and continue.
- Write all discovered candidates to the discovery queue, not the manifest.

Output:
- Updated pipeline/discovery-queue.md with new entries under a dated run header.
- Updated last_watcher_run timestamps in pipeline/manifest.json.
- A brief run summary appended to the discovery queue run header:
  sources queried, candidates found, failures encountered.
```

This template is stored at `templates/living-review-watcher-prompt.txt` for use by the scheduling mechanism. The scheduling tool substitutes `{project_path}` with the actual project directory path at invocation time.
