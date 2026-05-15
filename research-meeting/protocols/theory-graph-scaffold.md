# Theory-Graph Scaffolding Protocol

Load on-demand when the user requests scaffolding of a theory-graph vault for the active project. The cue is conversational ("scaffold a theory graph for this project" or equivalent); there is no CLI input field.

## Purpose

Create `<project_root>/theory/` for a project that does not yet have one. After scaffolding completes, the proposal-13 detection signature passes on the next session and the vault-first regime becomes active for the project.

This protocol is a **one-shot** operation per project. Re-running on a project that already has a vault either aborts, augments a missing piece, or overwrites — never silently destroys existing content.

## Inputs

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `project_root` | yes | resolved `active_project` from SKILL.md input | absolute path to the project root |
| `manuscript_root` | no | `TBD` | absolute path to the LaTeX manuscript root, or the literal string `TBD` if no manuscript exists yet |
| `install_hook` | no | ask user | whether to write `<project_root>/.claude/settings.json` SessionStart hook |
| `manuscript_path_prefix_strip` | no | `src/main/` | path-prefix strip for normalising manuscript-anchor paths |
| `manuscript_label_kinds` | no | Hawkes default | list of LaTeX label-kind prefixes to verify |

## Refuse-to-Overwrite Rule

Before any write, test `<project_root>/theory/` for existence and content:

1. **Does not exist.** Proceed.
2. **Exists and is empty.** Proceed.
3. **Exists and contains files.** Stop. Report the current state to the user (number of files, presence of `_scripts/`, presence of `_meta/`). Ask: abort, augment a specific missing piece, or overwrite?
   - **Augment:** Skip steps that would overwrite existing content; create only the missing pieces.
   - **Overwrite:** Confirm a second time explicitly. Then proceed as if the directory were empty (existing files are replaced).

The scaffolder never deletes or moves existing files without the explicit two-step overwrite confirmation.

## Procedure

### Step 1 — Resolve and validate inputs

1. Resolve `project_root` from the active session. If unresolved, ask the user.
2. Ask for `manuscript_root` if not supplied. If the user has no manuscript yet, accept `TBD` and proceed.
3. Ask whether to install the SessionStart hook.

### Step 2 — Apply the refuse-to-overwrite rule

Test the current state of `<project_root>/theory/`. Branch per the rule above.

### Step 3 — Create the directory tree

```
mkdir -p <project_root>/theory/{_archive,_meta,_scripts,assumptions,case-studies,corollaries,corollary-proofs,definitions,lemma-proofs,lemmas,notation,remarks,theorem-proofs,theorems}
```

### Step 4 — Copy the verifier with constant substitution

1. Copy `<research-meeting-root>/templates/theory-graph/scripts/check_theory_graph.py` to `<project_root>/theory/_scripts/check_theory_graph.py`.
2. Substitute placeholders:
   - `{{VAULT_ROOT}}` → `<project_root>/theory`
   - `{{MANUSCRIPT_ROOT}}` → `<manuscript_root>` (literal `TBD` if applicable)

### Step 5 — Write `_meta/config.yaml`

Copy `<research-meeting-root>/templates/theory-graph/config.yaml.template` to `<project_root>/theory/_meta/config.yaml`. Substitute:
- `{{PROJECT_ROOT}}` → `<project_root>`
- `{{MANUSCRIPT_ROOT}}` → `<manuscript_root>`

### Step 6 — Write `_meta/severity-overrides.yaml`

Copy `<research-meeting-root>/templates/theory-graph/severity-overrides.yaml.template` to `<project_root>/theory/_meta/severity-overrides.yaml`. No substitution needed.

If `manuscript_root` is **not** `TBD`, the scaffolder asks: should V9–V14 keep their default severities (file is deleted) or stay downgraded (file kept)? Default action: keep the file as-is; user can prune later.

### Step 7 — Write `_meta/_verifier-report.md`

Write a one-line stub: `# Verifier Report\n\n(No verifier run yet. The next session will populate this.)`

### Step 8 — Write the stub node

Copy `<research-meeting-root>/templates/theory-graph/stub-node.md` to `<project_root>/theory/notation/_stub.md`. Substitute:
- `{{SCAFFOLD_DATE}}` → today's date (`YYYY-MM-DD`)

### Step 9 — Install the SessionStart hook (optional)

If the user opted in:

1. Read `<project_root>/.claude/settings.json` if it exists.
2. Read `<research-meeting-root>/templates/theory-graph/session-start-hook.json.template` and substitute `{{PROJECT_ROOT}}` and `{{MANUSCRIPT_ROOT}}`.
3. If `<project_root>/.claude/settings.json` does not exist: create it with the substituted hook content.
4. If it exists: merge the SessionStart hook into the existing `hooks.SessionStart` array. If a SessionStart hook with the same command already exists, skip and report; if a different SessionStart hook exists, append (do not overwrite) and surface the merge state to the user.

### Step 10 — Completion report

Print to the user:

```
Theory graph scaffolded at <project_root>/theory/.
  - Verifier: _scripts/check_theory_graph.py (manuscript_root=<value>)
  - Stub node: notation/_stub.md
  - Severity overrides: <kept | not written>
  - SessionStart hook: <installed | declined | merged | conflict>

Detection signature passes from the next session forward. Use
theory-vault-writer 'add-object' to create the first real theoretical node;
the scaffold stub will be removed automatically once that node lands.
```

## Failure Handling

- `mkdir` fails — abort and report. Do not partial-write.
- Template file missing under `<research-meeting-root>/templates/theory-graph/` — abort with a clear error; the skill installation is incomplete.
- Substitution fails (placeholder not found in template) — abort and report which placeholder is missing.
- Hook merge encounters an irresolvable conflict — leave the existing `settings.json` unchanged, surface the conflict, and report.

## Cross-references

- `SKILL.md` Session Conduct → Theory graph → "Scaffolding on request" — entry point.
- `SKILL.md` Session Conduct → Theory graph (Detection) — the signature this scaffold satisfies.
- `protocols/subagent-delegation.md` §5 Vault-first awareness — the scaffolder is exempt (it creates the canonical surface rather than editing inside one).
- `theory-vault-writer/SKILL.md` `add-object` — the authoring counterpart that removes the stub after the first real node.
- `templates/theory-graph/` — all template files used by this protocol.
