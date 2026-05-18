---
name: lean-translator
description: Optional Lean 4 verification companion for a project's theory graph — translates vault statement+proof nodes into Lean, treats compilation as advisory warning, never gates work.
version: 0.1.0
---

# Lean Translator

## Mission

Provide an optional, opt-in Lean 4 verification layer over a project's theory-graph vault. For projects that opt in, the skill scaffolds a per-vault Lean project at `<project_root>/theory/lean/`, classifies vault nodes by Mathlib-coverage and atomization status, dispatches per-node translator subagents that produce Lean files and iterate against compiler feedback, and surfaces the resulting verification status as advisory information to the human reader.

Lean's verdict is a warning surface, never a gate. The human reading of every proof remains the source of truth.

## Inputs

The skill is invoked conversationally through one of its operations. There is no programmatic call protocol; the agent infers the operation from the request.

| Field | Description |
|-------|-------------|
| `operation` | One of: `scaffold-lean-project`, `audit`, `translate`, `verify`, `digest`. |
| `vault_root` | Path to a project's theory-graph vault. Default: `<project_root>/theory/` of the active research-meeting project. |
| `node_id` | Required only for `translate`. The vault node to translate (e.g., `theorems/T_3`). |

Typical invocations:

- "scaffold lean translation for this project" → `scaffold-lean-project`
- "run the lean audit" → `audit`
- "translate L_5 to lean" → `translate` with `node_id=lemmas/L_5`
- "what's the lean status?" → `verify` + `digest`

## Hard Boundaries

- Lean verification is **advisory only**. It never blocks vault edits, never blocks subagent dispatch, never enters a hard gate.
- The skill never modifies vault content (statement or proof markdown). It only writes to `<vault>/lean/` and to vault frontmatter status fields.
- The skill never commits or pushes to the source repository. Commits remain the user's responsibility.
- The skill does not invent statement-level mathematical content. If a translation requires a definition not in Mathlib and not in the project's local Lean library, the translator marks the attempt as `failed` with a `dep-mismatch` diagnostic — it does not silently axiomatize foundational objects.

## Dependencies

| Dependency | Type | When Invoked |
|------------|------|-------------|
| `theory-vault-writer` | hard | Maintains the vault frontmatter `lean_status` field through aggressive stale-marking on any vault edit. The `add-object` operation initializes `lean_status: not-attempted` on new nodes. |
| `memory-retriever` | soft | Loads `feedback_depersonalize_published_skill_examples` and any writing-style memories before translator subagent dispatch. |
| `research-meeting` | soft (consumer) | The meeting agent invokes this skill's operations and surfaces results in chat. |

## Load Order

1. This file (`SKILL.md`) — loaded when the meeting agent dispatches a `lean-translator` operation.
2. The protocol file for the specific operation — loaded on demand from `protocols/`.
3. `roles/translator.md` — loaded only when `translate` dispatches its subagent.

Protocols and roles are eligible for context eviction after their operation completes.

## Operations

The skill exposes five operations, each routed to a protocol file under `protocols/`.

| Operation | Protocol | Purpose |
|-----------|----------|---------|
| `scaffold-lean-project` | `protocols/scaffold-lean-project.md` | Create `<project_root>/theory/lean/` from templates for a vault that has none. One-shot per project. |
| `audit` | `protocols/audit.md` | Classify every vault node by dependency-class (Mathlib-stable / Mathlib-blocked / mixed) and atomization-class (already-atomic / too-coarse). Produces `<vault>/lean/_meta/triage.csv`. |
| `translate` | `protocols/translate.md` | Per-node Lean translation dispatch. Foreground subagent with cost surfacing before launch. |
| `verify` | `protocols/verify.md` | Run all Lean files in the vault, emit canonical status summary line. Background-runnable. |
| `digest` | `protocols/digest.md` | Produce the failed-attempt rollup for session-start handoff sections and mid-session pull requests. |

## Trust Model

Three rules constitute the trust posture:

1. **Never blocks.** No operation in this skill produces a hard gate. The structural verifier from the theory-graph layer (proposal 13) remains the only gate that blocks theoretical-content subagent dispatches; Lean verification is parallel to it, not part of it.
2. **Never invalidates.** A `failed` Lean status does not invalidate a vault node's human-reviewed proof. Failure is a signal to investigate, not a verdict.
3. **Human reading is canonical.** Lean-verified status is supplementary evidence, not a substitute for human review. The statement-parity gate (see `protocols/translate.md`) requires explicit user approval of each Lean statement before any `verified` badge attaches; until then the badge reads `verified-pending-review`.

This trust posture is the load-bearing constraint of the skill. Implementers should not weaken it without explicit user authorization.

## Vault Frontmatter Contract

Every vault node in a Lean-enabled project carries the following Lean-related frontmatter fields. `theory-vault-writer` initializes and maintains them; `lean-translator` reads and updates them. Vaults without a Lean project (no `<project_root>/theory/lean/`) carry no Lean frontmatter.

| Field | Type | Initialized by | Updated by | Description |
|-------|------|----------------|-----------|-------------|
| `lean_status` | enum (see below) | `theory-vault-writer add-object` | both | Current verification state of the vault node's Lean translation. |
| `lean_file` | path or `null` | `theory-vault-writer add-object` | `lean-translator translate` | Relative path from vault root to the translated Lean file. `null` until first translation. |
| `lean_attempted_at` | ISO-8601 timestamp or `null` | `theory-vault-writer add-object` | `lean-translator translate` | Timestamp of the most recent translator dispatch. `null` until first translation. |
| `lean_attempt_count` | int | `theory-vault-writer add-object` | `lean-translator translate` | Number of translator dispatches attempted on this node. Reset to `0` on vault edits that invalidate the translation. |
| `lean_diagnostics_class` | enum or `null` | — | `lean-translator translate` | On `failed` status, one of `translation-bug`, `dep-mismatch`, `proof-gap`. `null` otherwise. |
| `lean_status_prior` | enum or `null` | — | `theory-vault-writer` on stale | The status this node held before going stale. Preserved for audit when re-translation is attempted. |
| `lean_statement_parity_recheck_required` | bool | — | `theory-vault-writer` on statement edit | If `true`, the next translator dispatch must re-fire the statement-parity human gate even if compilation succeeds. |

### `lean_status` values

| Value | Meaning |
|-------|---------|
| `not-attempted` | No translator dispatch has run. Default for newly created nodes when a Lean project is present. |
| `mathlib-blocked` | Audit (Phase 0) classified this node as depending on a mathematical object not covered by stable Mathlib (e.g., counting-process compensators). Translation will not be attempted in v1. |
| `verified-pending-review` | Translator dispatch produced a Lean file that compiles cleanly; statement-parity human review has not yet happened. Lean badge displayed with the "pending" qualifier. |
| `verified` | Statement-parity human review approved the Lean statement as faithful to the vault statement. Full advisory badge. |
| `verified-local-axioms` | Same as `verified`, but the translator introduced inline `axiom` declarations or substantive ad-hoc local `def`s of foundational stochastic terms to bridge a Mathlib gap. Badge carries the qualifier and the user knows to discount. |
| `failed` | Translator dispatch exhausted its iteration budget without compiling. `lean_diagnostics_class` populated with the failure-class label. |
| `stale` | Vault content (statement or proof) was edited after the most recent successful translation. Prior status preserved under `lean_status_prior`. Re-translation queued at next translator opportunity. |

### Invariants

1. If `lean_status` is `verified` or `verified-local-axioms`, the human must have approved statement parity on this exact Lean statement. Editing the vault statement (without re-translation) violates the invariant; `theory-vault-writer` enforces this by flipping the status to `stale` on any statement edit.
2. If `lean_file` is not `null`, the file must exist at `<project_root>/<lean_file>`. The verifier script (`check_lean.py`) does not validate this; it is the translator's responsibility on each dispatch.
3. `lean_attempt_count` and `lean_attempted_at` must move together: a non-`null` timestamp implies a positive count.

## Cross-Skill Coordination

`theory-vault-writer` maintains the `lean_status` field on vault edits. See `~/.claude/skills/theory-vault-writer/SKILL.md` § "Lean translation coordination" for the coordination protocol (added in T-EU-4).

## Examples

See `examples/synthetic/cauchy-schwarz/` for a worked end-to-end example (vault statement + proof, Lean translation, statement-parity diff). This synthetic example is the skill's self-illustration — it contains no project-specific or research-bound content and is what role files and protocol example blocks reference. *Authored in T-EU-10; placeholder pending.*
