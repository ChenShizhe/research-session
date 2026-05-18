#!/usr/bin/env python3
"""
check_lean.py — Lean translator verifier.

Emits a canonical one-line status summary of a project's Lean translation state,
aggregating vault frontmatter and Lake build status.

Usage:
    python3 check_lean.py [--vault-root PATH]

If --vault-root is not given, walks up from CWD looking for a `theory/` directory.

Canonical output:
    lean: nodes=N verified=V failed=F stale=S not-attempted=A pending-review=R

Special outputs:
    lean: not-installed       — no theory/lean/ directory present
    lean: error <reason>      — lake or other tooling unavailable

Exit codes:
    0   — output emitted successfully (regardless of build status)
    1   — fatal error (no vault, lake missing, etc.); error line still emitted
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("lean: error (PyYAML not installed; run `pip install pyyaml`)")
    sys.exit(1)


STATUS_VALUES = {
    "not-attempted",
    "mathlib-blocked",
    "verified-pending-review",
    "verified",
    "verified-local-axioms",
    "failed",
    "stale",
}

VAULT_SUBDIRS = {
    "theorems", "lemmas", "corollaries", "definitions",
    "assumptions", "notation", "remarks", "case-studies",
    "theorem-proofs", "lemma-proofs", "corollary-proofs",
}


def find_vault_root(start: Path) -> Path | None:
    """Walk up from start looking for a directory containing theory/."""
    p = start.resolve()
    while p != p.parent:
        if (p / "theory").is_dir():
            return p
        p = p.parent
    return None


def read_frontmatter(md_path: Path) -> dict | None:
    """Parse YAML frontmatter from a markdown file. Returns dict, {}, or None on failure."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    try:
        data = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else {}


def walk_vault_nodes(vault_root: Path):
    """Yield (node_id, frontmatter_dict) for each vault markdown node."""
    theory = vault_root / "theory"
    if not theory.is_dir():
        return
    for kind_dir in sorted(theory.iterdir()):
        if not kind_dir.is_dir():
            continue
        if kind_dir.name.startswith("_") or kind_dir.name not in VAULT_SUBDIRS:
            continue
        for md in sorted(kind_dir.glob("*.md")):
            fm = read_frontmatter(md)
            if fm is None:
                continue
            node_id = f"{kind_dir.name}/{md.stem}"
            yield node_id, fm


def run_lake_build(lean_root: Path, timeout: int = 3600) -> tuple[int, str]:
    """Run `lake build` in lean_root. Returns (exit_code, combined_output)."""
    lake_bin = "lake"
    fallback = Path.home() / ".elan" / "bin" / "lake"
    if fallback.exists():
        lake_bin = str(fallback)
    try:
        result = subprocess.run(
            [lake_bin, "build"],
            cwd=str(lean_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "lake build timeout"
    except FileNotFoundError:
        return -2, "lake not found in PATH or ~/.elan/bin/"


def main():
    parser = argparse.ArgumentParser(description="Lean translator verifier")
    parser.add_argument("--vault-root", type=Path, default=None,
                        help="Path to vault root (default: walk up from CWD)")
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip `lake build`; report frontmatter-only status")
    parser.add_argument("--build-timeout", type=int, default=3600,
                        help="Seconds for lake build timeout (default: 3600)")
    args = parser.parse_args()

    vault_root = args.vault_root or find_vault_root(Path.cwd())
    if vault_root is None:
        print("lean: error (no vault detected from CWD; pass --vault-root)")
        return 1

    lean_root = vault_root / "theory" / "lean"
    if not lean_root.is_dir():
        print("lean: not-installed")
        return 0

    # Tally vault frontmatter by status.
    counts = {k: 0 for k in STATUS_VALUES}
    total = 0
    for _node_id, fm in walk_vault_nodes(vault_root):
        total += 1
        status = fm.get("lean_status", "not-attempted")
        if status not in counts:
            status = "not-attempted"
        counts[status] += 1

    # Optionally run lake build to surface compile state.
    # The build's exit code is informational only — frontmatter is the source
    # of truth for per-node status (the translator updates it on each dispatch).
    build_note = ""
    if not args.skip_build:
        exit_code, output = run_lake_build(lean_root, timeout=args.build_timeout)
        if exit_code == -2:
            print(f"lean: error ({output})")
            return 1
        if exit_code == -1:
            build_note = " (build timeout)"
        elif exit_code != 0:
            build_note = " (build has errors — see lake output)"

    # Canonical summary line.
    verified = counts["verified"] + counts["verified-local-axioms"]
    failed = counts["failed"]
    stale = counts["stale"]
    not_attempted = counts["not-attempted"] + counts["mathlib-blocked"]
    pending_review = counts["verified-pending-review"]

    print(
        f"lean: nodes={total} verified={verified} failed={failed} "
        f"stale={stale} not-attempted={not_attempted} "
        f"pending-review={pending_review}{build_note}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
