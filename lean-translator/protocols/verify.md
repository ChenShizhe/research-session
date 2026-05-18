# Protocol: `verify`

## Purpose

Run the Lean verifier on a project's vault and emit the canonical status summary line. Thin wrapper around `_scripts/check_lean.py`.

## Invocation cues

- "verify lean"
- "lean verifier"
- "what's the lean build status?"
- "check the lean translations"

## Prerequisites

- `<vault_root>/theory/lean/` exists
- `lake` accessible (full path under `~/.elan/bin/` accepted)

## Foreground mode

When the user asks for status synchronously, run:

```
python3 <vault_root>/theory/lean/_scripts/check_lean.py --skip-build
```

`--skip-build` makes it nearly instantaneous (frontmatter-only aggregation, no `lake build` invoked). Use when the user wants a quick status read.

Surface the canonical line directly:

```
lean: nodes=197 verified=12 failed=8 stale=3 not-attempted=174 pending-review=0
```

## Background mode (full build)

When the user asks for an authoritative compile-check (or as part of the session-close re-verification), drop `--skip-build` and dispatch via `Bash run_in_background: true`:

```
python3 <vault_root>/theory/lean/_scripts/check_lean.py --build-timeout 1800
```

Wall-clock: 5–60 minutes depending on vault size and Mathlib cache state. The notification fires on completion; surface the canonical line at that point, not before.

## Hook integration

The `SessionStart` hook installed by `scaffold-lean-project` (Step 9, opt-in) runs the verifier with `--skip-build` automatically at every session start. The structural verifier from proposal 13 emits its own line; the Lean verifier emits a second line parallel to it. Both are picked up by `research-meeting/protocols/session-startup.md` Step 5e (after the T-EU-8 extension lands).

Canonical emit format (must match exactly for hook parsing):

```
lean: nodes=N verified=V failed=F stale=S not-attempted=A pending-review=R
```

Optional suffix on build failure: `(build has errors — see lake output)` or `(build timeout)`.

## What `verify` does NOT do

- Does not modify vault frontmatter (the translator owns frontmatter updates).
- Does not classify nodes (that is `audit`'s job).
- Does not produce diagnostics rollups (that is `digest`'s job).
- Does not auto-trigger re-translation of failed nodes.
