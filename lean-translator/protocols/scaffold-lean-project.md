# Protocol: `scaffold-lean-project`

## Purpose

Create `<project_root>/theory/lean/` for a project that has a theory-graph vault but no Lean project yet. One-shot per project. Idempotent against accidental re-invocation via the refuse-to-overwrite rule.

## Invocation cues

The agent infers this operation from phrases such as:

- "scaffold lean translation for this project"
- "set up lean translation here"
- "add lean to this vault"
- "I want to start lean-translator on this project"

## Prerequisites

- Project root has a `theory/` directory with at least one populated subdirectory (the theory-graph detection signature from proposal 13).
- `elan`, `lean`, and `lake` are installed and accessible (full path under `~/.elan/bin/` is acceptable if PATH is not refreshed).
- The skill has been loaded (this protocol resolves to `lean-translator`'s templates directory).

## Inputs (collected conversationally if not provided)

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `project_root` | yes | active-project root from research-meeting | resolved at session start |
| `project_namespace` | yes | derived from project name (PascalCase) | confirmed with user before substitution |
| `lean_version` | no | latest stable Lean 4 release | overrideable for Mathlib-compatibility |
| `mathlib_version` | no | latest Mathlib release matching `lean_version` | overrideable |

## Steps

1. **Detect existing Lean project.** Check `<project_root>/theory/lean/`. If it exists, abort with: "theory/lean/ already present. Use `audit` or `translate` operations; this protocol does not overwrite." Refuse to proceed. End.

2. **Confirm project namespace.** Propose a `project_namespace` derived from the project's directory name (PascalCase, no special characters). Surface to user: "I'll use namespace `<NAMESPACE>`. Override?" Accept user override before continuing.

3. **Resolve Lean and Mathlib versions.** Default to the toolchain `~/.elan/bin/elan show active-toolchain` reports for Lean. For Mathlib, query the leanprover-community Mathlib repository's current release tag or use `main`. Surface to user: "Lean `<VERSION>`, Mathlib `<VERSION>`. Override?" Accept overrides.

4. **Create directory structure.** Create:
   - `<project_root>/theory/lean/`
   - `<project_root>/theory/lean/lib/<NAMESPACE>/Translated/`
   - `<project_root>/theory/lean/lib/<NAMESPACE>/Translated/{Theorems,Lemmas,Corollaries,Definitions,Assumptions,Notation,Remarks,CaseStudies}/` (matches vault subdirectory pattern)
   - `<project_root>/theory/lean/lib/<NAMESPACE>/ProjectLib/`
   - `<project_root>/theory/lean/_meta/`
   - `<project_root>/theory/lean/_attempts/`
   - `<project_root>/theory/lean/_scripts/`

5. **Copy and substitute templates.** From `~/Documents/skills/research-session/lean-translator/templates/lean-project/`:
   - `lakefile.toml.template` → `<project_root>/theory/lean/lakefile.toml` with `{{PROJECT_NAMESPACE}}` and `{{MATHLIB_VERSION}}` substituted
   - `lean-toolchain.template` → `<project_root>/theory/lean/lean-toolchain` with `{{LEAN_VERSION}}` substituted
   - `_meta/config.yaml.template` → `<project_root>/theory/lean/_meta/config.yaml` with all three placeholders substituted
   - `lib/namespace-readme.md.template` → `<project_root>/theory/lean/lib/<NAMESPACE>/README.md`
   - `lib/project-lib-stub.lean.template` → `<project_root>/theory/lean/lib/<NAMESPACE>/ProjectLib/Empty.lean`

6. **Copy the verifier script.** Copy `~/Documents/skills/research-session/lean-translator/_scripts/check_lean.py` to `<project_root>/theory/lean/_scripts/check_lean.py` (no substitution required — the script discovers its vault root at runtime).

7. **Copy and seed classification word lists.** Copy `~/Documents/skills/research-session/lean-translator/_scripts/mathlib-stable-terms.txt` and `point-process-terms.txt` to `<project_root>/theory/lean/_meta/`. These are user-editable; they ship with conservative defaults.

8. **Initialize Lake.** Run `cd <project_root>/theory/lean && lake update` to populate `lake-manifest.json` from the Mathlib dependency. Surface wall-clock cost: typically 5–15 minutes for first run. **Do not run `lake exe cache get` here** — defer to the user (the Mathlib build cache fetch is 30–60 minutes and should be an explicit choice).

9. **Optional: install SessionStart hook.** Ask the user: "Install a `SessionStart` hook so the Lean verifier line appears at session start? (y/n)". If yes, copy `~/Documents/skills/research-session/lean-translator/templates/session-start-hook.json.template` and merge into `<project_root>/.claude/settings.json` (preserve any existing hooks; do not silently overwrite).

10. **Surface scaffold summary.** Report to user:
    - Namespace chosen
    - Lean and Mathlib versions pinned
    - Verifier script location
    - Recommended next step: "Run `lake exe cache get` (~30–60 min, ~5 GB) before the first translator dispatch, or skip and let the first translation trigger a full build."

## Refuse-to-overwrite rule (Step 1 expanded)

If any of these files exist at scaffold time, abort:

- `<project_root>/theory/lean/lakefile.toml`
- `<project_root>/theory/lean/lean-toolchain`
- `<project_root>/theory/lean/_meta/config.yaml`

The agent does not offer "force overwrite" by default. If the user explicitly says "overwrite the existing Lean project", a two-step confirmation is required: first list every file that would be overwritten, then ask again. Even then, the existing files are moved to `<project_root>/theory/lean/_overwritten-<timestamp>/` rather than deleted.

## Scaffolder is exempt from vault-first awareness

This operation creates the canonical Lean surface; it cannot itself be vault-first because there is no Lean surface to defer to before scaffolding. The vault-first hard gate from proposal 13's subagent-delegation §5 explicitly exempts scaffold operations.

## Post-scaffold state

- `<project_root>/theory/lean/` exists with a valid Lake project structure
- The verifier script can be run: `python3 <project_root>/theory/lean/_scripts/check_lean.py` emits `lean: nodes=N verified=0 failed=0 stale=0 not-attempted=N pending-review=0` (no nodes translated yet)
- Vault frontmatter is unchanged; the `add-object` operation of `theory-vault-writer` will start initializing `lean_status: not-attempted` on subsequently-created nodes
- For pre-existing vault nodes, the `audit` operation must run next to populate frontmatter and produce the triage CSV
