# Protocol: `translate`

## Purpose

Orchestrate a per-node Lean translation dispatch. The meeting agent invokes this protocol when the user asks to translate a specific vault node (or when batch-translating a queue of nodes). The protocol handles cost surfacing, the subagent dispatch itself, post-dispatch frontmatter reconciliation, and chat surfacing of the outcome.

The actual translation work is done by the `translator` subagent defined in `roles/translator.md`. This protocol is the wrapper around that dispatch.

## Invocation cues

The agent infers this operation from phrases such as:

- "translate L_5 to lean"
- "try lean on theorem 3"
- "run translator on the cauchy-schwarz lemma"
- "translate the next pending node"

## Prerequisites

- `<project_root>/theory/lean/` exists (scaffolded via `scaffold-lean-project`)
- Vault node has `lean_status` in {`not-attempted`, `failed`, `stale`} — translation skipped on already-`verified`, `verified-local-axioms`, `verified-pending-review`, or `mathlib-blocked` (unless user explicitly forces re-translation)
- `lake` is installed and reachable (full path under `~/.elan/bin/` accepted)

## Steps

### 1. Resolve the target node

- Accept a `node_id` from the invocation (e.g., `theorems/T_3`, `lemmas/L_5`) or infer from context (`the cauchy-schwarz lemma` → look up by title).
- Verify the vault statement and proof files exist.
- Read vault frontmatter; confirm current `lean_status` permits a dispatch (see Prerequisites).
- If status is `mathlib-blocked`, ask the user: "this node is mathlib-blocked per the audit. Force-translate anyway? (y/n)". Proceed only on explicit y.

### 2. Pre-dispatch cost surfacing

Estimate token and wall-clock cost before launching the subagent. Format:

```
dispatch: <node-id>
  est tokens     ~K        (statement body ~X chars + proof body ~Y chars + iteration budget K=5)
  est wall-clock ~M min    (per-iteration lake build ~T min on this vault)
  proceed? (y/n)
```

Wait for user confirmation. The estimate format is informational; the user is the gate.

Estimation heuristics:
- **Tokens:** ~(statement_chars + proof_chars) * 6 (subagent reads vault + writes Lean + reads compiler output) * iteration_budget
- **Wall-clock:** measure prior `lake build` time on this vault (cached in `_meta/last-build-seconds.txt`), multiply by iteration_budget; on first dispatch, estimate 5 min per iteration before measurement

### 3. Dispatch the translator subagent

Dispatch as a **foreground** subagent (not background — the user has authorized this dispatch and may want to interrupt). Brief:

```
Role: lean-translator (see roles/translator.md)

Inputs:
  vault_statement_file: <abs path>
  vault_proof_file: <abs path>
  target_lean_file: <abs path under <project_root>/theory/lean/lib/<NS>/Translated/<Kind>/<NodeId>.lean>
  project_lean_root: <abs path to <project_root>/theory/lean/>
  project_namespace: <NS, from _meta/config.yaml>
  iteration_budget: 5
  existing_translations: <list of vault nodes with lean_status in {verified, verified-local-axioms}>

Constraints:
  - Anti-hallucination discipline is non-negotiable (see role file)
  - Do not edit vault content
  - Do not modify ProjectLib/
  - On terminal failure, write _attempts/<node-id>.lean-attempt.md and update vault frontmatter to failed
  - On success, update vault frontmatter to verified-pending-review (or verified-local-axioms if inline axioms detected)

Memory loads:
  - feedback_depersonalize_published_skill_examples (if working on the synthetic surrogate)

Reporting:
  - On success: one-line `translation success: <node-id> -> <lean_file>`
  - On failure: one-line `translation failed: <node-id> (diagnostics: <class>)`
  - In either case: terminal exit
```

### 4. Reconcile frontmatter

After the subagent returns, re-read the vault frontmatter to confirm the expected update landed. Sanity checks:

- If subagent reported success, `lean_status` must be `verified-pending-review` or `verified-local-axioms`
- If subagent reported failure, `lean_status` must be `failed` and `_attempts/<node-id>.lean-attempt.md` must exist
- If mismatch, log a process error to `<project_lean_root>/_attempts/_process-errors.log` and surface to user — do not auto-correct

### 5. Surface outcome

Per the failure-surfacing policy from proposal 15 (pull-on-demand mid-session + push at session-start), this protocol surfaces the immediate dispatch outcome in chat at the time of completion (since the user explicitly initiated the dispatch and is waiting). Format:

**On success (status: `verified-pending-review`):**
```
translation success: <node-id> -> <relative lean file path>
status: verified-pending-review
next step: statement-parity human gate — run statement-parity review on this node when ready
```

**On success (status: `verified-local-axioms`):**
```
translation success: <node-id> -> <relative lean file path>
status: verified-local-axioms (inline axioms or local stochastic defs detected — discount accordingly)
next step: statement-parity human gate
```

**On failure:**
```
translation failed: <node-id>
diagnostics: <class>
attempt file: <relative path to _attempts/<node-id>.lean-attempt.md>
iterations consumed: <N>/<K>
```

### 6. (Optional) Statement-parity gate handoff

If the user asks immediately "show me the statement parity" or "let's review", proceed to the statement-parity protocol (separate flow, not part of `translate`). Otherwise leave the node at `verified-pending-review` for later review via the `digest` operation.

## Batch translation

For batch dispatch (e.g., "translate the next ten pending-review nodes from the audit triage"), wrap this protocol in a loop, with one pre-dispatch confirmation up front for the whole batch (rather than per-node confirmation). The user authorizes the batch; per-node failures do not halt the batch (the failures land in `_attempts/` and surface in the final batch summary).

Batch summary format:

```
batch translation complete: N nodes dispatched, V verified-pending-review, A verified-local-axioms, F failed
verified-pending-review: <list of node ids>
verified-local-axioms: <list of node ids>
failed: <list of node ids> (see _attempts/ for diagnostics)
```

## Background batch (Phase 5 scale-up)

The Phase 5 scale-up runs as a long background batch via `_scripts/batch_translate.sh` (authored as part of T-EU-14 Branch A). That script invokes this protocol's subagent dispatch loop in a non-interactive context, writes per-node results into frontmatter as they complete, and surfaces a summary in the next session's handoff. Background batch does not surface per-dispatch outcomes in chat; only the rolled-up digest.
