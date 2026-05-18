# Protocol: `audit`

## Purpose

Phase 0 of the lean-translator lifecycle. Walks every vault node and classifies each by two orthogonal dimensions — dependency class (Mathlib-stable / Mathlib-blocked / mixed / unknown) and atomization class (already-atomic / too-coarse-needs-split). Produces `<vault_root>/theory/lean/_meta/triage.csv`, from which the pilot candidate pool is drawn.

## Invocation cues

- "run the lean audit"
- "classify the vault for translation"
- "what's the pilot candidate pool?"
- "audit the vault"

## Prerequisites

- `<vault_root>/theory/lean/` exists (scaffolded via `scaffold-lean-project`)
- `_meta/mathlib-stable-terms.txt` and `_meta/point-process-terms.txt` present (copied during scaffold)
- `_meta/config.yaml` present (atomization thresholds read from here, falling back to defaults if absent)

## Steps

### 1. Resolve vault root

From the active research-meeting project root, look for `<project_root>/theory/`. If not present, abort with: "no vault detected — `theory-vault-writer` must run first".

### 2. Confirm word-list freshness

Read `_meta/mathlib-stable-terms.txt` and `_meta/point-process-terms.txt`. Surface to user: "Audit will use word-lists with `<A>` stable terms and `<B>` blocked terms. Last modified `<DATE>`. Proceed? (y/n)". The user may want to update lists before the audit fires (especially in early sessions when defaults haven't been tuned).

### 3. Dispatch the classifier

Run `python3 <vault_root>/theory/lean/_scripts/classify_node.py --vault-root <vault_root>`. The script walks the vault, classifies each node, writes `triage.csv`.

Wall-clock: ~1 second per 100 vault nodes (file IO dominated; no Lean compile in this step).

### 4. Surface the classification summary

After the classifier completes, read `triage.csv` and report a one-screen summary:

```
audit complete: N nodes classified, written to <triage.csv>

dep_class breakdown:
  mathlib-stable:   <count>
  mathlib-blocked:  <count>
  mixed:            <count>
  unknown:          <count>

atom_class breakdown:
  already-atomic:           <count>
  too-coarse-needs-split:   <count>

recommended action breakdown:
  attempt-translation:        <count>   <- pilot candidate pool
  defer-mathlib-blocked:      <count>
  split-first:                <count>   <- candidates for theory-vault-writer to atomize
  review-manual:              <count>
```

### 5. Surface the pilot candidate list

Extract every row with `recommended_action == attempt-translation` and surface the first 20 by `node_id`:

```
Pilot candidate pool (first 20):
  <node_id>     (<kind>)     body=<W> words    invocations=<N>
  ...
```

If the pool has fewer than 5 nodes, flag as a yellow alert: "pool too small for the pilot's success criterion (need ≥5). Consider extending the allowlist or splitting coarse nodes first."

### 6. Frontmatter pre-population (optional, off by default)

Ask the user: "Pre-populate vault frontmatter `lean_status` from the triage? This sets `mathlib-blocked` on blocked nodes (else leaves as `not-attempted`). (y/n)". On `y`, walk the triage and update vault frontmatter accordingly — single batch operation, no per-node confirmation.

Off-by-default because the user may want to spot-check the classifier before committing to per-node frontmatter writes.

## Re-running the audit

The audit is idempotent and incremental: re-running overwrites `triage.csv` with current state. The classifier always re-reads every node — there is no caching by content hash at this stage (the audit is fast enough that caching adds complexity without benefit).

If the user updates the word-lists, re-running the audit picks up the changes immediately.

## What the audit does NOT do

- Does not compile any Lean code (the audit is text-classification only).
- Does not dispatch translator subagents (that is the `translate` protocol).
- Does not modify vault statement or proof body content.
- Does not write to the `Translated/` Lean tree.
- Does not check whether referenced Mathlib lemmas actually exist — the classification is heuristic (term presence in the dependencies/body), not a Lean-level semantic check. A node classified `mathlib-stable` may still fail translation if the proof uses Mathlib idioms in an unexpected way; the audit is a filter, not a guarantee.
