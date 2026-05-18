#!/usr/bin/env python3
"""
classify_node.py — vault-node audit classifier.

Walks every vault node under <vault_root>/theory/ and writes a triage CSV
that the lean-translator skill uses to select translation candidates.

For each node, classifies two orthogonal dimensions:

  dep_class:   mathlib-stable | mathlib-blocked | mixed
  atom_class:  already-atomic | too-coarse-needs-split

Output: <vault_root>/theory/lean/_meta/triage.csv with columns:
  node_id, kind, dep_class, atom_class, recommended_action,
  body_word_count, lemma_invocation_count, compound_step_flag

Usage:
    python3 classify_node.py [--vault-root PATH]

Reads classifier word-lists from:
    <vault_root>/theory/lean/_meta/mathlib-stable-terms.txt
    <vault_root>/theory/lean/_meta/point-process-terms.txt

If those files are not present at the per-vault location, falls back to:
    ~/Documents/skills/research-session/lean-translator/_scripts/<filename>
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML not installed (run `pip install pyyaml`)", file=sys.stderr)
    sys.exit(1)


VAULT_SUBDIRS = {
    "theorems", "lemmas", "corollaries", "definitions",
    "assumptions", "notation", "remarks", "case-studies",
    "theorem-proofs", "lemma-proofs", "corollary-proofs",
}

DEFAULT_ATOM_MAX_WORDS = 200
DEFAULT_ATOM_MAX_LEMMA_INVOKES = 3


def find_vault_root(start: Path) -> Path | None:
    p = start.resolve()
    while p != p.parent:
        if (p / "theory").is_dir():
            return p
        p = p.parent
    return None


def load_term_list(vault_root: Path, filename: str) -> list[str]:
    """Load a word-list file, comments stripped, lowercased."""
    per_vault = vault_root / "theory" / "lean" / "_meta" / filename
    fallback = Path.home() / "Documents/skills/research-session/lean-translator/_scripts" / filename
    src = per_vault if per_vault.exists() else fallback
    if not src.exists():
        return []
    terms = []
    for line in src.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        terms.append(s.lower())
    return terms


def load_atomization_config(vault_root: Path) -> dict:
    """Read atomization thresholds from _meta/config.yaml, fall back to defaults."""
    cfg_path = vault_root / "theory" / "lean" / "_meta" / "config.yaml"
    if not cfg_path.exists():
        return {
            "max_proof_words": DEFAULT_ATOM_MAX_WORDS,
            "max_distinct_lemma_invocations": DEFAULT_ATOM_MAX_LEMMA_INVOKES,
            "flag_compound_steps": True,
        }
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        data = {}
    a = data.get("atomization", {})
    return {
        "max_proof_words": a.get("max_proof_words", DEFAULT_ATOM_MAX_WORDS),
        "max_distinct_lemma_invocations": a.get(
            "max_distinct_lemma_invocations", DEFAULT_ATOM_MAX_LEMMA_INVOKES
        ),
        "flag_compound_steps": a.get("flag_compound_steps", True),
    }


def read_frontmatter_and_body(md_path: Path) -> tuple[dict, str]:
    """Returns (frontmatter_dict, body_text). Empty dict / empty body on parse failure."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, ""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    body = text[end + 4:]
    return fm, body


def classify_dependency(text: str, stable_terms: list[str],
                        blocked_terms: list[str]) -> str:
    """Returns mathlib-stable | mathlib-blocked | mixed | unknown."""
    text_lc = text.lower()
    stable_hits = any(term in text_lc for term in stable_terms)
    blocked_hits = any(term in text_lc for term in blocked_terms)
    if blocked_hits and stable_hits:
        return "mixed"
    if blocked_hits:
        return "mathlib-blocked"
    if stable_hits:
        return "mathlib-stable"
    return "unknown"


def classify_atomization(body: str, cfg: dict) -> tuple[str, int, int, bool]:
    """Returns (atom_class, word_count, lemma_invoke_count, compound_flag)."""
    words = body.split()
    word_count = len(words)

    # Lemma invocations: count distinct wiki-link refs to lemmas/theorems/etc.
    invokes = set()
    for m in re.findall(r"\[\[([^\]]+?)\]\]", body):
        invokes.add(m.strip().lower())
    invoke_count = len(invokes)

    # Compound steps: "by X and Y", "X, and Y, and", etc.
    compound_flag = False
    if cfg["flag_compound_steps"]:
        if re.search(r"\bby\s+\w+\s+(and|together with|combined with)\b",
                     body, re.IGNORECASE):
            compound_flag = True
        elif re.search(r"\b(and|together with)\s+\w+\s*,\s*\w+\s+(implies|yields|gives)\b",
                       body, re.IGNORECASE):
            compound_flag = True

    too_coarse = (
        word_count > cfg["max_proof_words"]
        or invoke_count > cfg["max_distinct_lemma_invocations"]
        or compound_flag
    )
    return ("too-coarse-needs-split" if too_coarse else "already-atomic",
            word_count, invoke_count, compound_flag)


def recommend(dep_class: str, atom_class: str) -> str:
    if dep_class == "mathlib-blocked":
        return "defer-mathlib-blocked"
    if dep_class == "unknown":
        return "review-manual"
    if atom_class == "too-coarse-needs-split":
        return "split-first"
    if dep_class == "mixed":
        return "review-manual"
    return "attempt-translation"


def walk_vault(vault_root: Path):
    theory = vault_root / "theory"
    for kind_dir in sorted(theory.iterdir()):
        if not kind_dir.is_dir():
            continue
        if kind_dir.name.startswith("_") or kind_dir.name not in VAULT_SUBDIRS:
            continue
        for md in sorted(kind_dir.glob("*.md")):
            fm, body = read_frontmatter_and_body(md)
            yield kind_dir.name, md.stem, fm, body


def main():
    parser = argparse.ArgumentParser(description="Vault audit classifier")
    parser.add_argument("--vault-root", type=Path, default=None,
                        help="Path to vault root (default: walk up from CWD)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output CSV path (default: <vault>/theory/lean/_meta/triage.csv)")
    args = parser.parse_args()

    vault_root = args.vault_root or find_vault_root(Path.cwd())
    if vault_root is None:
        print("error: no vault detected from CWD; pass --vault-root", file=sys.stderr)
        return 1

    out_path = args.output
    if out_path is None:
        out_path = vault_root / "theory" / "lean" / "_meta" / "triage.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stable_terms = load_term_list(vault_root, "mathlib-stable-terms.txt")
    blocked_terms = load_term_list(vault_root, "point-process-terms.txt")
    if not stable_terms or not blocked_terms:
        print("warning: term lists empty or missing", file=sys.stderr)
    atom_cfg = load_atomization_config(vault_root)

    rows = []
    for kind, stem, fm, body in walk_vault(vault_root):
        node_id = f"{kind}/{stem}"
        # Combine frontmatter dependencies (if any) + body for classification
        deps = fm.get("dependencies") or []
        if isinstance(deps, list):
            deps_text = " ".join(str(d) for d in deps)
        else:
            deps_text = str(deps)
        dep_text = deps_text + "\n" + body

        dep_class = classify_dependency(dep_text, stable_terms, blocked_terms)
        atom_class, wc, ic, cf = classify_atomization(body, atom_cfg)
        action = recommend(dep_class, atom_class)
        rows.append({
            "node_id": node_id,
            "kind": kind,
            "dep_class": dep_class,
            "atom_class": atom_class,
            "recommended_action": action,
            "body_word_count": wc,
            "lemma_invocation_count": ic,
            "compound_step_flag": cf,
        })

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "node_id", "kind", "dep_class", "atom_class", "recommended_action",
            "body_word_count", "lemma_invocation_count", "compound_step_flag",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"triage written: {out_path} ({len(rows)} nodes classified)")
    counts = {}
    for r in rows:
        key = (r["dep_class"], r["atom_class"])
        counts[key] = counts.get(key, 0) + 1
    print("summary by (dep_class, atom_class):")
    for (dep, atom), n in sorted(counts.items()):
        print(f"  {dep:18s} | {atom:24s} | {n:4d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
