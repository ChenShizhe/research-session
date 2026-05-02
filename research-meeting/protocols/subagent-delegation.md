# Subagent Delegation Protocol

This protocol governs when and how the main agent delegates work to one-shot subagents. Load on-demand when a delegation decision arises.

**Design reference:** `designs/P3-D1-subagent-delegation-and-output-format.md`

---

## 1. When to Delegate

Delegate when **any** of the following conditions hold:

| Condition | Signal | Example |
|-----------|--------|---------|
| **Context volume** | Task will produce or consume >~40kb of intermediate context | Reading 3 papers for a literature comparison |
| **Skill match** | An existing skill fits the task type and the task is self-contained | paper-reader for deep extraction, visual-architect for diagrams |
| **Parallelism** | Multiple independent sub-tasks can run concurrently | Searching for papers on two unrelated topics simultaneously |
| **Isolation** | Intermediate reasoning (failed attempts, verbose tool output) should not enter discussion context | Exploratory codebase search, debugging a simulation script |
| **Artifact production** | Primary output is a file, not a conversational response | Generating a figure, writing a proof outline to a file |

### When NOT to Delegate

| Condition | Rationale |
|-----------|-----------|
| **User interaction required** | Subagents cannot talk to the user. Tasks needing mid-execution clarification stay with the main agent. |
| **Tight discussion coupling** | The result needs iterative discussion. Delegation adds latency. |
| **Trivial tasks** | Fewer than ~3 tool calls — delegation overhead exceeds the work. |
| **Context-dependent judgment** | Task requires deep understanding of the current discussion's nuance that is hard to serialize. |

When uncertain whether to delegate, **ask the user**: "This might benefit from a subagent — should I delegate or handle it here?"

---

## 2. Delegation Depth: Light vs. Deep

| Tier | Description | Expected Duration | Output Budgets |
|------|-------------|-------------------|----------------|
| **Light** | Quick, bounded task. Fetch a fact, check a reference, extract a section, generate a diagram. | Minutes. Finishes within the current discussion flow. | Section budgets apply (see `templates/subagent-report.md`). |
| **Deep** | Substantial task. Survey a topic, read multiple papers, attempt several proof strategies. | Tens of minutes to hours. May outlast the current topic. | Executive Summary is still budgeted (5-25 lines). All other sections unconstrained. |

When uncertain about tier, ask the user: "This could be a quick lookup or a deeper investigation — which do you have in mind?" Record the tier in the delegation brief.

Most in-session subagents are **light**. Deep delegations are typically background tasks where the user wants thorough coverage.

---

## 3. Foreground vs. Background

- **Foreground (blocking):** Main agent waits for completion. Use when the discussion depends on the result.
- **Background (concurrent):** Main agent continues the discussion. Use when the result is needed later.

Light delegations are typically foreground. Deep delegations are typically background. Either combination is valid — a deep foreground task is appropriate when the user explicitly wants to wait.

---

## 4. The Delegation Brief

When delegating, compose a **delegation brief** — conceptually a five-tuple:

```
(Objective, Context Files, Constraints, Output Spec, Quality Criteria)
```

The brief is expressed in natural language, not JSON or API-specific format. Any runtime that supports spawning a subprocess with a text instruction can execute this protocol.

### 4.1 Objective (required)

A clear, specific statement of the deliverable, scope boundary, and non-obvious constraints.

**Bad example:**

> Look into kernel smoothing methods.

This is too vague. The subagent has no scope boundary, no deliverable format, and no way to know when it is done.

**Good example:**

> Produce a structured comparison of three kernel smoothing bandwidth selectors (Silverman's rule, cross-validation, plug-in) for multivariate point process cross-covariance estimation. Focus on: asymptotic properties, computational cost, known failure modes. Write the output to `subagent-outputs/YYYY-MM-DD-bandwidth-selector-comparison.md`.

This states the deliverable, scopes to three specific methods, names the evaluation axes, and specifies the output path.

### 4.2 Context Files (required when relevant)

An explicit list of files the subagent should read for background. Select the **minimal set** needed — the subagent's context window is finite and overloading it degrades quality.

```
Read these files for context before starting:
- <project_root>/domain-prior.md
- <project_root>/memory/latest-summary.md
- <project_root>/manuscript/sections/methodology.tex
```

### 4.3 Constraints (optional)

Limits on scope, effort, or approach:
- Token/effort hints: "Aim for a concise report, not an exhaustive survey."
- Tool restrictions: "Use only read-only tools — do not modify any files except the output."
- Time sensitivity: "This is blocking our discussion — prioritize speed over completeness."

### 4.4 Output Specification (required)

- **Output path:** Always within `subagent-outputs/` at the project root. Naming: `YYYY-MM-DD-<task-slug>.md`.
- **Output format:** Follow `templates/subagent-report.md`.
- Any task-specific requirements (e.g., "Include BibTeX entries for all cited papers").

### 4.5 Quality Criteria (optional but recommended)

How the main agent will evaluate success:
- "The comparison should cover all three methods. If information on one is unavailable, state this explicitly rather than guessing."
- "Each claim must have a citation or reference to a specific section of a paper."

### Full Brief Example

**Bad brief:**

> Find papers about point process bandwidth selection and summarize them.

Missing: scope boundary, output path, format reference, quality criteria. The subagent will guess at all of these.

**Good brief:**

> **Objective:** Compare Silverman's rule, cross-validation, and plug-in bandwidth selectors for multivariate point process cross-covariance estimation. Cover asymptotic properties, computational cost, and known failure modes.
>
> **Context files:**
> - `<project_root>/domain-prior.md`
> - `<project_root>/memory/latest-summary.md`
>
> **Constraints:** This is a light delegation. Aim for a concise comparison, not an exhaustive survey. Read-only tools only — do not modify any files except the output.
>
> **Output:** Write to `subagent-outputs/2026-04-01-bandwidth-selector-comparison.md` following the format in `templates/subagent-report.md`. Depth: light.
>
> **Quality criteria:** All three methods must be covered. If a method lacks accessible literature, state this explicitly. Each claim needs a citation.

---

## 5. Context File Selection Guidance

Select context files based on the task type:

| Task Type | Recommended Context Files |
|-----------|--------------------------|
| Literature-related | `domain-prior.md`, `memory/latest-summary.md`, relevant citadel entries, `references/` entries |
| Theory/proof | `domain-prior.md`, `memory/latest-summary.md`, relevant manuscript sections, prior proof attempts |
| Code/simulation | `domain-prior.md`, relevant code files, prior simulation results in `results/` |
| Visualization | `domain-prior.md`, data files or results to visualize, style preferences from `memory/latest-summary.md` |
| General research | `domain-prior.md`, `memory/latest-summary.md` (always safe defaults) |

The two universal defaults are **`domain-prior.md`** (project grounding) and **`memory/latest-summary.md`** (institutional knowledge). If a subagent needs project context, these two files are almost always relevant.

### Error log awareness

The Error Knowledge section of `memory/latest-summary.md` (Tier 1) and the structured detail files under `memory/errors/` (Tier 2) are **standing context for every subagent dispatch**, not conditional on the task "plausibly" repeating a logged error. The earlier conditional rule failed in practice because the judgment call was where the inclusion got skipped. Treat the error log the same way you treat `domain-prior.md`: it is part of project grounding.

#### Tier 1 — always included, unconditionally

Every subagent brief's Context Files section must include:

- `<project_root>/memory/latest-summary.md` — the full file (the Error Knowledge section is one of seven sections). The Tier 1 section has a ~10-line budget, so the cost of always including it is negligible.

#### Tier 2 — top-k retrieval via hybrid query, never full-dump

The Tier 2 detail files at `<project_root>/memory/errors/` are not all included. Including them all would degrade the subagent's performance via context rot: the published literature on long-input behavior shows that performance on retrieval-and-instruction tasks degrades monotonically as the input grows, driven by the *volume of irrelevant content*, not just total length. Instead, retrieve the top-k matching files (default k = 3, max k = 5) using the **hybrid query** mechanism:

1. **Query construction.** The main agent rewrites the dispatched task description into a small set of focused sub-queries (typically 2–4 short topic strings drawn from the task objective and the subagent's role). Sub-query construction is LLM-side; the retrieval over them is deterministic.
2. **Retrieval.** Invoke `memory-retriever` with the hybrid sub-queries scoped to `<project_root>/memory/errors/`. The retriever scores each Tier 2 file by `recency + importance + relevance` (the Generative Agents formula): exponential recency decay (~30-day half-life), the 1–10 importance score assigned at promotion time, and cosine similarity to the sub-queries. Initial weights are equal; tunable later.
3. **Inclusion.** The top-k results are added to the brief's Context Files section. If retrieval returns fewer than k results, include what came back; do not pad with low-relevance entries.
4. **Surfacing.** When Tier 2 files are included, the brief's Constraints section lists the matched error-ids and surfaces the **positive rule** field of each (the "when situation S occurs, do Y" reformulation written at promotion). The full description, root cause, and prevention notes remain in the file body for the subagent to consult on demand; the positive rule is the actionable summary that appears in the brief itself.

#### Constraints directive (standing)

The brief's Constraints section includes:

> *Tier 1 Error Knowledge is always present in `memory/latest-summary.md`. Tier 2 files matched by the dispatch retrieval are listed below with their positive rules. If your task pattern resembles a logged error, adjust your approach to follow the positive rule.*

The subagent is not expected to echo back which errors it consulted. Consumption is silent; the evidence of success is the absence of recurrence.

#### Accumulation and maintenance

Errors accumulate across sessions. The Tier 1 budget is enforced via maintenance compaction (see `SKILL.md` Maintenance Session Protocol). The Tier 2 file count triggers a maintenance recommendation when it reaches 10; beyond that, the retrieval mechanism still works but maintenance is overdue. See `protocols/session-close.md` Step 1.6 for where Tier 2 files are written and where the importance / positive-rule fields are assigned.

---

## 6. Reintegration Protocol

When a subagent completes (foreground or background):

**Step 1: Read frontmatter + Executive Summary only.**
Read the first ~20 lines of the output file. Check the `status` field.

**Step 2: Evaluate.**

| Status | Action |
|--------|--------|
| `completed` | Read Executive Summary. If clear and actionable, incorporate findings into the discussion. |
| `partial` | Read Executive Summary + Limitations. Report to user what was accomplished and what's missing. User decides next step. |
| `failed` | Read Executive Summary (which explains the failure) + Limitations. Report to user. Do not retry automatically. |

**Step 3: Report to user.**
Summarize the subagent's findings concisely in the discussion. Paraphrase and contextualize — do not paste the full Executive Summary. If the user wants detail, read deeper into the file.

**Step 4: Act on findings.**
Together with the user, decide what to do with the results:
- Update project state (add tasks, note findings for `latest-summary.md` update at session close, flag contradictions with existing knowledge).
- Delegate follow-up work (new subagent, same protocol).
- Discuss inline if findings raise questions.

The subagent output does not automatically trigger any of these actions — the main agent and user decide together.

### Reading Beyond the Summary

Read beyond the Executive Summary only when:
- The summary references a specific finding that needs elaboration.
- The user asks about methodology or limitations.
- The summary is ambiguous and more context would help.

Do **not** read the full report proactively. The full report may be 1-2k tokens; reading it unnecessarily erodes the discussion budget.

---

## 6.5. Vault-Write Decomposition

When a delegation produces content whose destination is the Citadel vault (`~/Documents/citadel/`), the delegation must be **decomposed** into two separate subagent calls:

1. **Content-producing delegation.** A subagent (specialist, paper-reader, any content producer) writes its artifact to `subagent-outputs/YYYY-MM-DD-<slug>.md` following the standard report format. This subagent must not write to `~/Documents/citadel/`.
2. **Vault-write delegation.** The main agent reintegrates the first delegation's output, then dispatches `knowledge-maester` as a separate subagent with the artifact as source material and the target vault path as a parameter. `knowledge-maester` performs the vault write.

The decomposition applies regardless of how simple the content is. Specialist briefs, paper extractions, analyses, reference notes — all follow this pattern. **No subagent other than `knowledge-maester` writes directly to `~/Documents/citadel/`.**

If a specialist role file (or equivalent) instructs the specialist to "write to the vault through knowledge-maester," that instruction is for the *main agent orchestrating the two-step dispatch*, not for the specialist subagent executing its one-shot task. Role files whose language implies the specialist itself can invoke `knowledge-maester` must be reworded.

### Why decomposition is required

Subagents are one-shot (§9): they execute to completion and terminate, and cannot spawn sub-delegations. When a main agent dispatches a single specialist subagent to do research + produce artifact + write to vault in one call, the specialist handles all three steps itself — it has no mechanism to invoke `knowledge-maester` from inside its own execution. The all-in-one dispatch is the natural failure mode whenever a main agent skips the extra delegation step, and the fallback behavior is typically a direct write to the vault that bypasses `knowledge-maester`'s sole-writer convention. Making the decomposition rule explicit makes it enforceable.

### The two-step dispatch template

```
Step 1 — Content-producing delegation:
  Objective: <produce the artifact that belongs in the vault>
  Output: subagent-outputs/YYYY-MM-DD-<slug>.md (NOT the vault)
  Constraint: Do not write to ~/Documents/citadel/. The main agent will
  route this artifact to knowledge-maester in a separate dispatch.

[Main agent reintegrates the first delegation's output per §6.]

Step 2 — Vault-write delegation:
  Skill: knowledge-maester
  Objective: Ingest <artifact> to <target vault path> using the appropriate
  ingestion script (ingest_report.py / ingest_paper.py / ingest_analysis.py /
  ingest_ticker.py / ingest_reference.py / etc., per knowledge-maester's
  ingestion contracts).
  Source: subagent-outputs/YYYY-MM-DD-<slug>.md
```

Compose both steps at the same time (the vault-write dispatch is not optional "if time allows"); the pair is a single unit of work.

---

## 7. Failure Handling

### 7.1 Failure Modes

| Failure Mode | Detection |
|-------------|-----------|
| **Timeout / max turns** | Runtime-enforced. Subagent exceeds turn limit or wall-clock timeout. |
| **No output file** | Main agent checks for expected file — it does not exist. |
| **Malformed output** | Output file exists but missing sections (no frontmatter, no Executive Summary). |
| **Low-quality output** | Output follows format but findings are superficial, incorrect, or off-topic. |
| **Subagent error** | Runtime error propagation (tool failure, permission denied, etc.). |

### 7.2 Responses

**Timeout / max turns:**
Report to user: "The [task] subagent timed out. [Partial results available at path / No output was produced.]" User decides: retry with narrower scope, investigate manually, or abandon.

**No output file:**
Report: "The [task] subagent completed but did not write an output file." Treat as failure. The subagent's return message may contain useful information — report it.

**Malformed output:**
Read whatever is there, extract what's useful. Report: "The subagent output is incomplete — missing [sections]. Here's what it did produce: [summary]."

**Low-quality output:**
If the Executive Summary doesn't answer the delegated question, say so. User decides whether to re-delegate with a more specific brief, handle inline, or accept as-is.

**Subagent error:**
Report the error to the user.

### 7.3 No Automatic Retry

The main agent does **not** automatically retry failed subagents. Reasons:

1. **Specification problems repeat.** Retrying with the same brief produces the same poor output — 42% of multi-agent failures stem from specification problems.
2. **Silent resource consumption.** Automatic retries consume context and time without user awareness.
3. **User decides.** The user should evaluate whether the task is worth retrying, needs a different approach, or should be handled inline.

The main agent may **suggest** a retry with a modified brief, but does not execute without user confirmation.

---

## 8. Turn Limits by Task Type

These are guidelines for composing the delegation brief. They are not hard-enforced by the skill — enforcement depends on the runtime.

| Task Type | Suggested Max Turns | Rationale |
|-----------|-------------------|-----------|
| Literature search (paper-discovery) | 30 | Multiple web searches and filtering |
| Deep paper reading (paper-reader) | 40 | Multi-section extraction from a single paper |
| Code review / debugging | 25 | Read + analyze + write findings |
| Proof checking | 20 | Focused reasoning on a specific proof |
| Diagram generation (visual-architect) | 15 | Relatively bounded output |
| Citadel lookup | 15 | Targeted vault traversal |
| Ad-hoc research | 25 | Default for untyped tasks |

Calibrate actual limits after real use. Record adjustments in the project's error knowledge if a task type consistently needs more or fewer turns.

---

## 9. Standing Instructions

- **Use advanced models for reasoning-heavy subagent tasks.** When the delegated task involves synthesis, proof-checking, multi-paper comparison, or other tasks that benefit from stronger reasoning, prefer a more capable model tier. Use faster/cheaper models for exploration, search, and mechanical extraction. This distinction helps any runtime pick the proper model tier when spawning a subagent.

  | Task characteristic | Recommended tier | Claude examples |
  |---------------------|-----------------|-----------------|
  | Synthesis, proof-checking, multi-paper comparison, novel analysis | Advanced (strongest reasoning) | Opus, Sonnet |
  | Targeted extraction, search, lookups, structured formatting | Standard (fast/cheap) | Haiku, Sonnet |

  *If using a non-Claude provider, substitute the provider's strongest reasoning model for the advanced tier and a cost-efficient model for the standard tier.* The per-skill model recommendations in §10 follow this same tiering — treat them as defaults that can be overridden when a specific delegation is unusually reasoning-heavy or unusually mechanical.
- **Subagents are one-shot.** They execute to completion, write their output, and terminate. They do not persist across conversation turns. Persistent subagents are Phase 4 scope.
- **The brief is the only interface.** There is no back-and-forth during execution. If the subagent needs clarification, it makes its best judgment and documents assumptions in its output.

---

## 10. Skill Delegation Profiles

This section provides concrete delegation profiles and brief templates for individual skills. Each profile specifies the default parameters for composing a delegation brief and a ready-to-use template. Profiles are derived from `designs/P3-D3-skill-integration.md`.

### 10.1 Paper-Reader

#### Delegation Profile

| Field | Value |
|-------|-------|
| **Skill** | `paper-reader` |
| **Depth** | Deep (multi-section extraction from a full paper) |
| **Mode** | Background (deep reading takes time; discussion can continue) |
| **Max turns** | 40 |
| **Model recommendation** | Sonnet or Opus (comprehension quality is critical for extraction accuracy) |
| **Citadel integration** | **Pre-check required.** Before reading from source, search the vault for an existing extraction. If a comprehensive citadel note already exists, use it as the primary source and delegate only the missing sections. See [Citadel Pre-Check](#citadel-pre-check) below. |

#### Citadel Pre-Check

The delegation brief must instruct the subagent to check the citadel before reading the paper from source:

```
Before reading the paper from source, check ~/Documents/citadel/ for an
existing note on this paper (search by author name and year in tags or
frontmatter). If a comprehensive extraction already exists, use it as the
primary source and supplement only what's missing.
```

This prevents redundant extraction when the vault already has a good note on the paper. Paper-reader is the most expensive delegation (40 max turns, deep), so vault pre-checks provide the highest savings here.

#### Delegation Brief Template

```
Objective: Read and extract structured findings from [paper citation].
Focus on: [specific sections or topics, e.g., "methodology, main theorem,
computational complexity"]. If no focus is specified, perform full extraction.

Context files:
- <project_root>/domain-prior.md
- <project_root>/memory/latest-summary.md
- [any prior subagent outputs on related papers]

Constraints:
- Follow the paper-reader skill instructions.
- Before reading from source, check ~/Documents/citadel/ for an existing
  note on this paper (search by author name and year in tags or frontmatter).
  If a comprehensive extraction already exists, use it as the primary source
  and supplement only what's missing.
- Write output to subagent-outputs/YYYY-MM-DD-paper-extraction-<author-year>.md
- If the paper is not accessible (no PDF, no citadel note, no web access),
  report this in the Executive Summary and set status: failed.

Output: Follow the format in templates/subagent-report.md. Depth: deep.
  Frontmatter must include skill_used: paper-reader and
  paper_citation: <full citation>.

Quality criteria:
- Each extracted claim must reference a specific section, theorem, or page
  of the paper. Vague citations ("somewhere in the paper") are not acceptable.
- The Executive Summary must state the paper's relevance to our project
  in 1-2 sentences.
- If any section of the paper is inaccessible or skipped, state this
  explicitly rather than guessing at content.
```

#### Output Format Notes

- **Frontmatter**: Standard subagent report schema. `skill_used: paper-reader`. Add `paper_citation: <full citation>` as an extra field.
- **Executive Summary**: Paper's main contribution, relevance to the project, key takeaways. Standard budget (5-25 lines for deep).
- **Key Findings**: Organized by paper section rather than by topic. Each section heading matches the paper's structure.
- **Methodology**: What the subagent did — which sections were read, what was skipped, whether the full PDF or a citadel note was used.
- **References**: The paper itself plus any cross-references cited within it that are relevant.

---

### 10.2 Paper-Discovery

#### Delegation Profile

| Field | Value |
|-------|-------|
| **Skill** | `paper-discovery` |
| **Depth** | Light (search + filter + candidate list) or Deep (comprehensive literature survey) |
| **Mode** | Background (web searches take time) |
| **Max turns** | 30 |
| **Model recommendation** | Sonnet (balance of search capability and cost) |
| **Citadel integration** | **Vault-first check.** Search the vault for existing coverage before external search. Categorize results as vault-existing vs. newly discovered. |

#### Vault-First Check

The delegation brief must instruct the subagent to search the vault before going external:

```
Before searching externally, check ~/Documents/citadel/ and the project's
references/ directory for existing notes on this topic. Report which papers
are already in the vault vs. newly discovered. This prevents recommending
papers the user has already processed.
```

Unlike paper-reader's pre-check (which can eliminate the task entirely), paper-discovery's vault-first check shapes the output categorization — the subagent must distinguish between known and new papers in its results.

#### Delegation Brief Template

```
Objective: Find [N] relevant papers on [topic] for [purpose].
Prioritize: [recency / foundational / methodological / empirical].

Context files:
- <project_root>/domain-prior.md
- <project_root>/memory/latest-summary.md
- <project_root>/references/ (existing reference list)

Constraints:
- Follow the paper-discovery skill instructions.
- Write output to subagent-outputs/YYYY-MM-DD-paper-discovery-<topic-slug>.md
- Before searching externally, check ~/Documents/citadel/ and the project's
  references/ directory for existing notes on this topic. Report which papers
  are already in the vault vs. newly discovered.
- Produce a paper_manifest.json if the paper-discovery skill requires it.

Output: Follow the format in templates/subagent-report.md.
  Depth: [light or deep, depending on the scope of the search].
  Frontmatter must include skill_used: paper-discovery,
  topic: <search topic>, and papers_found: <count>.

Quality criteria:
- Each candidate paper must include: title, authors, year, venue, and a
  1-2 sentence relevance assessment.
- Results must be categorized into: (1) Top Recommendations (new),
  (2) Already in Vault, and (3) Additional Candidates.
- Flag papers that are already in the citadel vault or references directory.
```

#### Output Format Notes

- **Frontmatter**: Standard subagent report schema. `skill_used: paper-discovery`. Add `topic: <search topic>` and `papers_found: <count>`.
- **Executive Summary**: How many papers found, top 3-5 recommendations with one-line justifications, what's already in the vault vs. new.
- **Key Findings**: Categorized into three groups:
  - **Top Recommendations (new)**: Newly discovered papers ranked by relevance.
  - **Already in Vault**: Papers that have existing citadel notes, with vault paths.
  - **Additional Candidates**: Lower-priority or tangential papers for completeness.
- **Artifacts**: `paper_manifest.json` if produced (referenced in `output_artifacts` frontmatter field).

---

### 10.3 Knowledge-Maester

#### Delegation Profile

| Field | Value |
|-------|-------|
| **Skill** | `knowledge-maester` |
| **Depth** | Light (targeted vault write or update) |
| **Mode** | Foreground or Background (foreground when the discussion needs confirmation that a note was written; background when batching vault updates at session close) |
| **Max turns** | 20 |
| **Model recommendation** | Sonnet (structured note production; reasoning demands are moderate) |
| **Citadel integration** | **IS the citadel writer.** This skill's primary purpose is creating, updating, and organizing notes in `~/Documents/citadel/`. All output is written directly to the vault, not to `subagent-outputs/`. |

#### Vault Write Behavior

Knowledge-maester is unique among delegated skills: its output destination is the citadel vault itself, not the standard `subagent-outputs/` directory. The delegation brief must specify:

- The **target vault path** within `~/Documents/citadel/` (e.g., `~/Documents/citadel/papers/`, `~/Documents/citadel/concepts/`).
- Whether the task is a **new note** or an **update** to an existing note.
- The **source material** — typically a subagent report from paper-reader or paper-discovery, discussion findings, or user-supplied content.

Because knowledge-maester writes to the shared vault, the main agent should verify the output after completion (read the frontmatter of the created/updated note) to confirm it was placed correctly.

#### Delegation Brief Template

```
Objective: [Create / Update] a citadel note for [subject — paper, concept,
method, etc.]. [If updating: specify what to add or revise.]

Source material:
- [subagent-outputs/YYYY-MM-DD-paper-extraction-<slug>.md, or other source]
- [additional context files if needed]

Context files:
- <project_root>/domain-prior.md
- ~/Documents/citadel/ (search for existing notes on this subject before
  creating a new one — update rather than duplicate)

Constraints:
- Follow the knowledge-maester skill instructions.
- Write output directly to ~/Documents/citadel/<appropriate-subdirectory>/
  using the vault's naming and frontmatter conventions.
- Do NOT write to subagent-outputs/. The vault IS the output destination.
- If an existing note on this subject is found in the vault, update it
  rather than creating a duplicate. Preserve existing content that is
  still accurate.

Output: A well-structured citadel note with proper frontmatter (tags,
  aliases, links to related notes). Follow vault conventions for the
  note type (paper note, concept note, method note, etc.).

Quality criteria:
- Frontmatter must include appropriate tags, aliases, and links.
- Content must be sourced — no unsupported claims. Reference the source
  material explicitly.
- The note should be self-contained: a reader unfamiliar with the
  discussion should understand it from the note alone.
- If updating, clearly integrate new material with existing content
  rather than appending disjoint sections.
```

#### Output Format Notes

- **Output destination**: `~/Documents/citadel/`, not `subagent-outputs/`. This is the key distinction from other delegated skills.
- **Format**: Follows the citadel vault's own conventions (Obsidian-compatible markdown with YAML frontmatter), not `templates/subagent-report.md`.
- **Verification**: After completion, the main agent reads the created/updated note's frontmatter to confirm correct placement and tagging.

---

### 10.4 Visual-Architect

#### Delegation Profile

| Field | Value |
|-------|-------|
| **Skill** | `visual-architect` |
| **Depth** | Light (diagram or figure generation is bounded) |
| **Mode** | Foreground (diagrams are typically needed in the current discussion flow) |
| **Max turns** | 15 |
| **Model recommendation** | Sonnet (diagram specification is structured, not reasoning-heavy) |
| **Citadel integration** | Rarely needed. Visual-architect produces diagrams for the current project, not vault notes. Only reference the citadel if the diagram must depict vault structure or citadel-sourced relationships. |

#### Delegation Brief Template

```
Objective: Generate a [diagram type — architecture diagram, flowchart,
concept map, data pipeline, proof dependency graph, etc.] showing
[what the diagram should depict].

Context files:
- <project_root>/domain-prior.md
- [specific files containing the structures or relationships to visualize]
- [prior diagrams to maintain visual consistency, if any]

Constraints:
- Follow the visual-architect skill instructions.
- Write output to subagent-outputs/YYYY-MM-DD-diagram-<slug>.md
  (containing the diagram source code and any explanatory notes).
- Generated diagram artifacts (SVG, PNG, or diagram-as-code source)
  should be placed alongside the report or in the project's figures/
  directory as specified.
- Use [Mermaid / TikZ / other format] for the diagram source.

Output: Follow the format in templates/subagent-report.md. Depth: light.
  Frontmatter must include skill_used: visual-architect and
  diagram_type: <type>.

Quality criteria:
- The diagram must accurately represent the structures or relationships
  described in the context files. No invented nodes or connections.
- Labels must be legible and use terminology consistent with the project.
- The diagram should be self-explanatory with a brief caption or legend
  where needed.
- If the requested visualization is too complex for a single diagram,
  propose a decomposition in the Executive Summary rather than producing
  an unreadable diagram.
```

#### Output Format Notes

- **Frontmatter**: Standard subagent report schema. `skill_used: visual-architect`. Add `diagram_type: <type>`.
- **Executive Summary**: What the diagram shows, any design decisions made (layout choices, what was included/excluded), and caveats.
- **Key Findings**: The diagram source code (in a fenced code block) and any supporting notes on how to render or integrate it.
- **Artifacts**: The diagram file(s) referenced in `output_artifacts` frontmatter field.

---

### 10.5 Experience-Logger

> **This is NOT a subagent task.** Experience-logging stays with the main agent.

#### Rationale

Experience-logger is explicitly excluded from subagent delegation for the following reasons:

| Reason | Explanation |
|--------|-------------|
| **Requires session context** | Experience observations arise from the full arc of a conversation — delegation decisions, subagent outcomes, user corrections, workflow friction. A subagent cannot observe these; it only sees what is serialized into its brief. |
| **Requires subagent usage observations** | A key input to the experience log is how subagent delegations went during the session — which skills were used, whether they succeeded, what the turn counts looked like, and what the user thought of the results. The main agent is the only actor that observes all of this. |
| **Continuous, not discrete** | Experience entries accumulate throughout a session. Subagents are one-shot — they cannot observe an evolving conversation. |
| **Low overhead** | Writing an experience log entry is a few tool calls at most. It does not meet the delegation threshold (§1: "Fewer than ~3 tool calls — delegation overhead exceeds the work"). |

#### How the Main Agent Handles Experience-Logging

At session close (or at natural breakpoints), the main agent appends observations to the project's experience log. Observations should include:

- **Subagent usage**: Which skills were delegated, depth/mode used, whether the output was useful, and any turn-limit issues.
- **Workflow observations**: What went smoothly, what caused friction, and any patterns worth noting for future sessions.
- **User feedback**: Corrections or preferences expressed during the session that are worth recording beyond the immediate conversation.

These observations feed into the project's continuous improvement loop — they are the raw material for refining delegation briefs, adjusting turn limits, and evolving skill instructions over time.

---

## 11. Handoff Plan Format

A **handoff plan** is a self-contained specification for work that cannot be completed within the current agent session. Unlike a delegation brief (§4), which targets a single one-shot subagent, a handoff plan is designed for execution by a **future session**, a **batch/autonomous runner**, or a **sequence of subagent delegations**. Plans live in the project, not in subagent output — they are persistent project artifacts.

### 11.1 File Location

```
<project_root>/plans/YYYY-MM-DD-<task-slug>.md
```

Examples:
- `plans/2026-04-03-bandwidth-selector-survey.md`
- `plans/2026-04-05-proof-completeness-check.md`

The `plans/` directory is created at runtime on first use. Do not pre-create it.

### 11.2 Frontmatter Schema

Every handoff plan begins with YAML frontmatter:

```yaml
---
task: "<short human-readable task name>"
status: draft          # draft | approved | in-progress | completed | abandoned
created: YYYY-MM-DD
approved: YYYY-MM-DD   # null until approved
estimated_scope: light  # light | deep | multi-session
target_runner: future-session  # future-session | batch-runner | subagent-chain
dependencies:
  - "<path or identifier of prerequisite artifact>"
  - "<another dependency>"
tags:
  - "<project-relevant tag>"
  - "<another tag>"
---
```

#### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task` | string | yes | Short, descriptive name of the work to be done. |
| `status` | enum | yes | Current lifecycle state (see §11.4). |
| `created` | date | yes | Date the plan was drafted (`YYYY-MM-DD`). |
| `approved` | date | no | Date the plan was approved by the user. `null` or omitted while in `draft`. |
| `estimated_scope` | enum | yes | Expected effort: `light` (single session, <1 hour), `deep` (single session, 1-3 hours), `multi-session` (spans multiple sessions or runners). |
| `target_runner` | enum | yes | Who or what will execute the plan. |
| `dependencies` | list | no | Artifacts, files, or other plans that must exist before execution begins. Empty list if none. |
| `tags` | list | no | Free-form tags for filtering and discovery. |

#### `target_runner` Values

| Value | Meaning |
|-------|---------|
| `future-session` | A future interactive Claude session picks up the plan. |
| `batch-runner` | A batch/autonomous runner executes the plan without interactive oversight. |
| `subagent-chain` | The current or future main agent executes the plan as a sequence of subagent delegations, coordinating the handoffs. |

### 11.3 Body Sections

The plan body contains six sections in order. All sections are required; use "N/A" if a section is genuinely inapplicable.

#### Objective

A clear statement of the deliverable and scope boundary. Same intent as a delegation brief's Objective (§4.1), but scoped to potentially multi-step work.

```markdown
## Objective

Survey all bandwidth selector methods applicable to multivariate point process
cross-covariance estimation. Produce a structured comparison document covering
at least 5 methods, with a recommendation for our use case.
```

#### Background

Context that the executor needs but that is not captured in the context files alone. This section explains *why* the work matters and what prior attempts or decisions led to this plan.

```markdown
## Background

Our current methodology uses Silverman's rule, which assumes Gaussian marginals.
Early experiments (see `results/2026-03-sim-bandwidth/`) show systematic
under-smoothing for clustered processes. The session on 2026-03-28 identified
this as a priority gap — we need a principled alternative before drafting §4
of the manuscript.
```

#### Execution Steps

An ordered list of concrete steps the executor should follow. Each step should be actionable and verifiable. For `subagent-chain` plans, each step may map to a single subagent delegation.

```markdown
## Execution Steps

1. Search for papers on bandwidth selection for point process covariance
   estimation (paper-discovery, light).
2. Read the top 5 candidates in depth (paper-reader, deep — one delegation
   per paper).
3. Extract comparison axes from domain-prior.md: asymptotic rate, computational
   cost, smoothness assumptions, known failure modes.
4. Produce a structured comparison table in
   `subagent-outputs/YYYY-MM-DD-bandwidth-comparison.md`.
5. Write a 1-paragraph recommendation for our use case, referencing the
   comparison.
6. Create or update citadel notes for any newly read papers
   (knowledge-maester, light — batch at end).
```

#### Context Files

Files the executor should read before starting. Same purpose as §4.2, but may include more files since the scope is larger.

```markdown
## Context Files

- <project_root>/domain-prior.md
- <project_root>/memory/latest-summary.md
- <project_root>/results/2026-03-sim-bandwidth/summary.md
- <project_root>/manuscript/sections/methodology.tex
```

#### Expected Output

What artifacts the plan produces and where they should be written. Be specific about paths and formats.

```markdown
## Expected Output

- `subagent-outputs/YYYY-MM-DD-bandwidth-comparison.md` — structured comparison
  following `templates/subagent-report.md`, depth: deep.
- Citadel notes for each newly read paper in `~/Documents/citadel/papers/`.
- Updated `references/` entries for any papers not already tracked.
```

#### Success Criteria

How the main agent (or user) will evaluate whether the plan was successfully executed. These should be concrete and verifiable.

```markdown
## Success Criteria

- At least 5 methods are compared across all four axes (asymptotic rate,
  computational cost, smoothness assumptions, failure modes).
- Each claim in the comparison is cited to a specific paper and section.
- A clear recommendation is stated with justification.
- All newly read papers have citadel notes with proper frontmatter.
```

### 11.4 Lifecycle States

Plans move through a defined set of states:

```
draft ──► approved ──► in-progress ──► completed
                │                          │
                ▼                          ▼
            abandoned                  abandoned
```

| State | Meaning | Who transitions |
|-------|---------|-----------------|
| `draft` | Plan exists but has not been reviewed or approved. **Not executable.** | Main agent creates the draft. |
| `approved` | User has reviewed and approved the plan. Ready for execution. | User confirms (main agent updates `status` and sets `approved` date). |
| `in-progress` | Execution has begun. The executor updates this status when starting. | Executor (future session, batch runner, or subagent-chain coordinator). |
| `completed` | All success criteria are met. The executor updates this status when finished. | Executor, after verifying success criteria. |
| `abandoned` | Plan is no longer relevant or has been superseded. | User or main agent, with a note explaining why. |

**Key rule:** A plan in `draft` status must not be executed. The user must explicitly approve it first. This prevents the agent from acting on speculative plans.

### 11.5 Plan Generation Protocol

Creating and activating a handoff plan follows a four-step protocol:

#### Step 1: Draft

The main agent creates the plan file in `plans/` with `status: draft`. This typically happens when:
- A task is identified that exceeds the current session's scope.
- The user requests work to be done later or in a batch context.
- A multi-step investigation is planned during a research discussion.

The agent writes the full plan (frontmatter + all six body sections) and presents the plan to the user for review.

#### Step 2: Review

The user reviews the plan. The main agent should highlight:
- **Scope**: Is the `estimated_scope` realistic?
- **Dependencies**: Are all prerequisites available or will they block execution?
- **Steps**: Are the execution steps concrete enough for the target runner?
- **Success criteria**: Are they verifiable?

The user may request revisions. The main agent updates the plan file while it remains in `draft`.

#### Step 3: Approve

The user approves the plan. The main agent updates the frontmatter:
- `status: draft` → `status: approved`
- `approved: YYYY-MM-DD` (set to the current date)

After approval, the plan is ready for execution by its `target_runner`.

#### Step 4: Record

After execution completes (or is abandoned), the executor updates the plan status to `completed` or `abandoned` and adds a brief outcome note at the bottom of the plan:

```markdown
## Outcome

**Status:** completed
**Date:** 2026-04-05
**Summary:** All 5 methods compared. Recommended plug-in selector with
cross-validation fallback. See `subagent-outputs/2026-04-05-bandwidth-comparison.md`.
```

This section is appended — it does not replace any of the six body sections. The plan remains a historical record of what was intended and what happened.

### 11.6 Execution Patterns

Handoff plans support three execution patterns, determined by the `target_runner` field.

#### Pattern 1: Future Session (`target_runner: future-session`)

A future interactive Claude session picks up the plan. The user opens a new session and instructs the agent to execute the plan.

**Executor behavior:**
1. Read the plan file from `plans/`.
2. Verify `status: approved`. If not approved, stop and inform the user.
3. Update `status: in-progress`.
4. Execute the steps in order, using subagent delegation (§4) for individual steps where appropriate.
5. After all steps complete, verify success criteria.
6. Update `status: completed` and append the Outcome section.

**When to use:** Work that benefits from interactive oversight — the user can course-correct mid-execution.

#### Pattern 2: Batch Runner (`target_runner: batch-runner`)

A batch/autonomous runner executes the plan without interactive user oversight.

**Executor behavior:**
1. Read the plan file from `plans/`.
2. Verify `status: approved`.
3. Update `status: in-progress`.
4. Execute all steps autonomously. Since there is no user to ask for clarification, the plan must be **fully self-contained** — all ambiguities should have been resolved during the review step.
5. Write all outputs to the specified paths.
6. Update `status: completed` and append the Outcome section.

**When to use:** Well-defined, mechanical work that does not require judgment calls. The plan must be detailed enough that no interactive decisions are needed.

**Additional constraints for batch-runner plans:**
- Execution steps must be unambiguous — no "if unclear, ask the user" hedges.
- All context files must be accessible from the batch runner's environment.
- Success criteria must be machine-verifiable where possible.

#### Pattern 3: Subagent Chain (`target_runner: subagent-chain`)

The current or future main agent executes the plan as a coordinated sequence of subagent delegations.

**Executor behavior:**
1. Read the plan file from `plans/`.
2. Verify `status: approved`.
3. Update `status: in-progress`.
4. For each execution step, compose a delegation brief (§4) and delegate to an appropriate subagent. Reintegrate results (§6) between delegations.
5. The main agent coordinates: it carries context between steps, handles failures (§7), and decides whether to continue or abort.
6. After all steps complete, verify success criteria.
7. Update `status: completed` and append the Outcome section.

**When to use:** Multi-step investigations where each step produces output that informs the next. The main agent provides the continuity that one-shot subagents cannot.

**Relationship to delegation briefs:** Each execution step in a subagent-chain plan maps to one delegation brief. The plan is the overarching specification; the briefs are the per-step specifications. The plan's Context Files and Success Criteria inform every brief, but each brief has its own Objective, Constraints, and Output Spec tailored to that step.

### 11.7 Living Document Nature

A handoff plan is a **living document** — it may be updated during execution:

- **Step completion tracking:** The executor may add checkmarks or status annotations to individual execution steps as they complete.
- **Mid-execution amendments:** If execution reveals that a step needs modification (e.g., a dependency was wrong, an additional step is needed), the executor updates the plan before continuing. The plan always reflects the current intent, not just the original intent.
- **Scope adjustments:** If the work turns out to be larger or smaller than estimated, update `estimated_scope` and add a note explaining why.

However, the six body sections and frontmatter schema remain structurally stable — amendments modify content within sections, they do not reorganize the document.

### 11.8 Handoff Plan vs. Delegation Brief

| Dimension | Delegation Brief (§4) | Handoff Plan (§11) |
|-----------|----------------------|-------------------|
| **Scope** | Single one-shot subagent task | Multi-step or multi-session work |
| **Executor** | One subagent, running now | Future session, batch runner, or subagent chain |
| **Location** | Composed inline (not persisted as a file) | `plans/YYYY-MM-DD-<task-slug>.md` |
| **Approval** | Implicit (main agent decides to delegate) | Explicit (user must approve before execution) |
| **Lifecycle** | Fire-and-forget | Draft → Approved → In-Progress → Completed/Abandoned |
| **Structure** | 5-tuple: Objective, Context Files, Constraints, Output Spec, Quality Criteria | Frontmatter + 6 sections: Objective, Background, Execution Steps, Context Files, Expected Output, Success Criteria |
| **Persistence** | Transient (exists only in the delegation message) | Persistent project artifact |

When a task fits a single subagent, use a delegation brief. When the work is too large, spans sessions, or needs user approval before execution, create a handoff plan.
