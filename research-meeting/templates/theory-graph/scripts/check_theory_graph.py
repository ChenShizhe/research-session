#!/usr/bin/env python3
"""
check_theory_graph.py — verifier for the Hawkes theory vault.

Vault layout (under ~/Documents/Research/Hawkes/theory/):
  assumptions/      definitions/      notation/
  lemmas/           lemma-proofs/
  theorems/         theorem-proofs/
  corollaries/      corollary-proofs/
  case-studies/     remarks/
  _meta/            _scripts/

Each file is a markdown document with a YAML frontmatter block delimited by
`---` lines and a body. Checks V1-V14 (see design doc and module docstring
below) inspect frontmatter and body for graph-integrity, symbol-usage,
hypothesis-matching, transitive-assumption, symbol-clash, orphan-lemma,
missing-proof, citation-chain, manuscript-drift, manuscript-vault parity,
verbatim parity, orphan vault label, wikilink-resolution, and stale
line-anchor issues.

Limitations
-----------
- The vault frontmatter contains many bare bracketed strings such as
  `defined-in: [VERIFICATION-FINDING: ...]`. These break strict YAML
  parsing. The loader falls back to a tolerant key/value extractor when
  PyYAML rejects the block. Recovered records may miss nested structure
  (e.g., the `input.assumptions:` sub-list), so a few checks (V3, V4)
  are best-effort on files that need the fallback.
- V4 (transitive assumption tracking) walks the lemma-proof dependency
  graph and aggregates assumption labels found in the
  `uses-assumptions:` field of the proofs. Verification-finding strings
  are filtered out. Cycles are detected and broken.
- V8 (citation-chain) counts unique bibkeys; without a bibliography
  database, we only surface the cite-key inventory.
- V9 (drift) checks that the manuscript file exists and that the
  referenced label/line is plausible (label form: grep for ``\\label{<lbl>}``
  in the file; line form: file has at least that many lines).
- V10 (manuscript-to-vault parity) scans `<manuscript-root>/sections/`
  and `<manuscript-root>/appendices/` for `\\label{X}` where X matches
  `(thm|lmm|cor|asmp|def|rmk)::*` and confirms a vault file has
  frontmatter `label: X`. `eqn::*` labels are intentionally skipped
  because definition-kind vault files may carry them by convention.
- V11 (verbatim parity) for each vault file with a symbolic
  `manuscript-anchor` (form `<file>:<label>`), extracts the fenced
  verbatim block from the vault body and the `\\begin{...}\\label{<label>}
  ...\\end{...}` block from the manuscript, normalises both sides
  (strip LaTeX comments, canonicalise spacing commands, collapse
  whitespace), and compares bodies. The normaliser treats `\\,`,
  `\\!`, `\\:`, `\\;`, `\\ `, `\\quad`, `\\qquad`, `\\cdot`,
  `\\thinspace`, `\\medspace`, `\\thickspace` as a single canonical
  token, and drops both whole-line (`% ...`) and mid-line `%`-to-EOL
  LaTeX comments before comparison.
- V12 (orphan vault label) for each vault `label:` of the target kinds
  above, greps the manuscript for `\\ref`/`\\eqref`/`\\cref`/`\\label`
  occurrences; emits a warning when none are found. Deprecated and
  archive/infrastructure files are skipped.
- V13 (wikilink resolution) confirms every `[[X]]` wikilink target
  exists as `<X>.md` under `theory/` (excluding `_archive/`, `_meta/`,
  `_scripts/`).
- V14 (stale line-anchor) for vault files whose `manuscript-anchor` is
  in line-number form AND whose `label:` matches a manuscript `\\label{}`,
  confirms the line in the manuscript file matches the labelled object.
  Files whose `label:` is vault-internal (no manuscript counterpart) are
  exempt.

Usage
-----
    python3 check_theory_graph.py [--strict] [--check V1,V3]
                                  [--report-path <path>] [--vault <path>]
                                  [--manuscript-root <path>]
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:  # pragma: no cover - PyYAML is expected to be present
    HAVE_YAML = False


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Defaults below are placeholders substituted by the research-meeting
# theory-graph scaffolder at copy time. When the substituted values are
# absent (e.g., this template is run standalone), CLI args are required.
DEFAULT_VAULT = Path("{{VAULT_ROOT}}")
DEFAULT_MANUSCRIPT_ROOT = Path("{{MANUSCRIPT_ROOT}}")
DEFAULT_REPORT = DEFAULT_VAULT / "_meta/_verifier-report.md"

# Vault `manuscript-anchor` values store paths relative to the project root
# (e.g. `src/main/sections/04-...tex`). When the verifier is invoked with
# `--manuscript-root /.../src/main`, the leading `src/main/` segment must be
# stripped to resolve the anchor under the supplied root.
# Read from <vault>/_meta/config.yaml if present; otherwise fall back to the
# Hawkes default. The scaffolder writes the config at copy time.
_DEFAULT_MANUSCRIPT_PATH_PREFIX_STRIP = "src/main/"
MANUSCRIPT_PATH_PREFIX_STRIP = _DEFAULT_MANUSCRIPT_PATH_PREFIX_STRIP  # may be overridden by config load below

SUBDIRS = [
    "assumptions",
    "definitions",
    "notation",
    "lemmas",
    "lemma-proofs",
    "theorems",
    "theorem-proofs",
    "corollaries",
    "corollary-proofs",
    "case-studies",
    "remarks",
]

STATEMENT_KINDS = {"theorem-statement", "lemma-statement", "corollary-statement"}
PROOF_KINDS = {"theorem-proof", "lemma-proof", "corollary-proof"}

# Default severity per check. Tunable via _meta/verifier.yaml.
DEFAULT_SEVERITY = {
    "V1": "error",
    "V2": "warning",
    "V3": "error",
    "V4": "warning",
    "V5": "error",
    "V6": "warning",
    "V7": "error",
    "V8": "warning",
    "V9": "error",
    "V10": "error",
    "V11": "error",
    "V12": "warning",
    "V13": "warning",
    "V14": "warning",
}

CHECK_TITLES = {
    "V1": "Define-before-use (wiki-link target exists)",
    "V2": "Body-symbol scan (notation declared in frontmatter)",
    "V3": "Hypothesis matching (proof assumptions ⊆ statement assumptions)",
    "V4": "Transitive assumption tracking",
    "V5": "Symbol-clash detection",
    "V6": "Orphan-lemma detection",
    "V7": "Missing-proof detection",
    "V8": "Citation-chain inventory",
    "V9": "Manuscript-anchor drift detection",
    "V10": "Manuscript label has a vault node",
    "V11": "Vault verbatim block matches manuscript",
    "V12": "Vault label referenced in manuscript",
    "V13": "Wikilink targets resolve as exact basenames",
    "V14": "Manuscript-anchor line numbers match",
}

# Manuscript label kinds that V10, V12, V14 operate on.
# Read from <vault>/_meta/config.yaml if present; otherwise fall back to the
# Hawkes default.
_DEFAULT_MANUSCRIPT_LABEL_KINDS = ("thm", "lmm", "cor", "asmp", "def", "rmk")
MANUSCRIPT_LABEL_KINDS = _DEFAULT_MANUSCRIPT_LABEL_KINDS  # may be overridden by config load below


def _load_vault_config(vault_root: Path) -> dict:
    """Read <vault>/_meta/config.yaml when present. Tolerant on errors."""
    cfg_path = vault_root / "_meta" / "config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml  # PyYAML is already an implicit dep via frontmatter parsing
        with cfg_path.open() as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _apply_vault_config(vault_root: Path) -> None:
    """Side-effect: update module-level MANUSCRIPT_* globals from config."""
    global MANUSCRIPT_LABEL_KINDS, MANUSCRIPT_PATH_PREFIX_STRIP
    cfg = _load_vault_config(vault_root)
    kinds = cfg.get("manuscript_label_kinds")
    if isinstance(kinds, list) and kinds:
        MANUSCRIPT_LABEL_KINDS = tuple(str(k) for k in kinds)
    strip = cfg.get("manuscript_path_prefix_strip")
    if isinstance(strip, str):
        MANUSCRIPT_PATH_PREFIX_STRIP = strip


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Finding:
    check_id: str
    severity: str
    file: str  # relative to vault root
    message: str
    line: Optional[int] = None


@dataclasses.dataclass
class VaultFile:
    path: Path
    rel_path: str  # relative to vault root
    subdir: str
    stem: str
    raw: str
    frontmatter_text: str
    body: str
    fm: Dict
    fm_parse_ok: bool


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def split_frontmatter(text: str) -> Tuple[str, str]:
    """Return (frontmatter_text, body). frontmatter_text is empty if absent."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def _tolerant_yaml_load(fm_text: str) -> Dict:
    """
    Tolerant frontmatter parser. Handles the bracket-flow-sequence trap
    common in this vault (e.g. `defined-in: [VERIFICATION-FINDING: ...]`)
    by quoting any unquoted bracket-flow value that contains a colon or
    other YAML-unfriendly characters.
    """
    # First try strict parse.
    if HAVE_YAML:
        try:
            data = yaml.safe_load(fm_text)
            if isinstance(data, dict):
                return data
        except yaml.YAMLError:
            pass

    # Tolerant strategy: quote the offending values then re-attempt.
    fixed_lines: List[str] = []
    for line in fm_text.splitlines():
        stripped = line.lstrip()
        if (
            stripped.startswith("#")
            or not stripped
            or stripped.startswith("-")
        ):
            fixed_lines.append(line)
            continue
        # Look for `key: value` patterns where value starts with `[` and is
        # not a quoted YAML flow-sequence.
        m = re.match(r"^(\s*)([A-Za-z0-9_\-]+)\s*:\s*(.*)$", line)
        if not m:
            fixed_lines.append(line)
            continue
        indent, key, val = m.groups()
        val_strip = val.strip()
        if val_strip.startswith("[") and not val_strip.startswith('["') and not val_strip.startswith("['"):
            # Bare bracket value. Replace with a single-quoted string,
            # escaping any embedded single quotes.
            safe = val_strip.replace("'", "''")
            fixed_lines.append(f"{indent}{key}: '{safe}'")
        else:
            fixed_lines.append(line)
    repaired = "\n".join(fixed_lines)
    if HAVE_YAML:
        try:
            data = yaml.safe_load(repaired)
            if isinstance(data, dict):
                return data
        except yaml.YAMLError:
            pass

    # Last-resort: simple key-value extraction (lossy on nested structure).
    out: Dict = {}
    current_key: Optional[str] = None
    current_list: Optional[List[str]] = None
    for line in fm_text.splitlines():
        if re.match(r"^[A-Za-z0-9_\-]+\s*:\s*", line):
            m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", line)
            assert m
            current_key = m.group(1)
            val = m.group(2).strip()
            if val == "":
                current_list = []
                out[current_key] = current_list
            else:
                out[current_key] = val
                current_list = None
        elif line.lstrip().startswith("- ") and current_list is not None:
            current_list.append(line.lstrip()[2:].strip())
        # Indented mapping content under a key is dropped; flagged later.
    return out


def parse_file(path: Path, vault_root: Path) -> VaultFile:
    raw = path.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(raw)
    fm: Dict = {}
    parse_ok = True
    if fm_text:
        if HAVE_YAML:
            try:
                parsed = yaml.safe_load(fm_text)
                if isinstance(parsed, dict):
                    fm = parsed
                else:
                    parse_ok = False
                    fm = _tolerant_yaml_load(fm_text)
            except yaml.YAMLError:
                parse_ok = False
                fm = _tolerant_yaml_load(fm_text)
        else:
            parse_ok = False
            fm = _tolerant_yaml_load(fm_text)
    rel = str(path.relative_to(vault_root))
    return VaultFile(
        path=path,
        rel_path=rel,
        subdir=path.parent.name,
        stem=path.stem,
        raw=raw,
        frontmatter_text=fm_text,
        body=body,
        fm=fm,
        fm_parse_ok=parse_ok,
    )


# ---------------------------------------------------------------------------
# Helper extractors
# ---------------------------------------------------------------------------

WIKILINK_RE = re.compile(r"\[\[([^\[\]\|]+?)(?:\|[^\[\]]*)?\]\]")
LATEXSYMBOL_RE = re.compile(r"\\[A-Za-z]+(?:_\{[^}]*\}|\^\{[^}]*\}|_[A-Za-z0-9]|\^[A-Za-z0-9])?")
CITEP_RE = re.compile(r"\\cite[tpn]?\*?\{([^}]+)\}")
CFCITE_RE = re.compile(r"\[c\.f\.\s+([A-Za-z][A-Za-z0-9]+(?:\s+\d{4})?)\]")


def extract_wikilinks(text: str) -> List[Tuple[str, int]]:
    """Return list of (target, line_number_1based) for each [[target]]."""
    out: List[Tuple[str, int]] = []
    for line_idx, line in enumerate(text.splitlines(), start=1):
        for m in WIKILINK_RE.finditer(line):
            target = m.group(1).strip()
            out.append((target, line_idx))
    return out


def extract_bibkeys(text: str) -> Set[str]:
    keys: Set[str] = set()
    for m in CITEP_RE.finditer(text):
        for raw in m.group(1).split(","):
            k = raw.strip()
            if k:
                keys.add(k)
    for m in CFCITE_RE.finditer(text):
        keys.add(m.group(1).strip())
    return keys


def _normalize_label_ref(s: str) -> str:
    """Normalize a `[[file-stem]]` or `file-stem` reference to a vault stem."""
    s = s.strip()
    if s.startswith("[[") and s.endswith("]]"):
        s = s[2:-2]
    if "|" in s:
        s = s.split("|", 1)[0]
    return s.strip()


def _flatten_assumption_list(raw) -> List[str]:
    """Flatten a frontmatter assumption list into label strings, filtering
    verification-finding placeholders."""
    out: List[str] = []
    if raw is None:
        return out
    if isinstance(raw, str):
        items: Iterable = [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        return out
    for item in items:
        if not isinstance(item, str):
            continue
        s = item.strip()
        # Strip optional surrounding quotes.
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        if s.startswith("'") and s.endswith("'"):
            s = s[1:-1]
        if "VERIFICATION-FINDING" in s:
            continue
        # Drop comments after `#`.
        if "#" in s:
            s = s.split("#", 1)[0].strip()
        if s.startswith("[[") and s.endswith("]]"):
            s = s[2:-2]
        if s:
            out.append(s)
    return out


def _get_input_assumptions(fm: Dict) -> List[str]:
    inp = fm.get("input")
    if isinstance(inp, dict):
        return _flatten_assumption_list(inp.get("assumptions"))
    # Fallback: tolerant loader may have flattened the structure. Look for
    # raw frontmatter text below if needed.
    return []


def _get_uses_assumptions(fm: Dict) -> List[str]:
    return _flatten_assumption_list(fm.get("uses-assumptions"))


def _get_uses_lemmas(fm: Dict) -> List[str]:
    out: List[str] = []
    for raw in fm.get("uses-lemmas", []) or []:
        if not isinstance(raw, str):
            continue
        if "VERIFICATION-FINDING" in raw:
            continue
        s = raw.strip()
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        if "#" in s:
            s = s.split("#", 1)[0].strip()
        if s.startswith("[[") and s.endswith("]]"):
            s = s[2:-2]
        if s:
            out.append(s)
    return out


def _get_uses_notation(fm: Dict) -> List[str]:
    out: List[str] = []
    for raw in fm.get("uses-notation", []) or []:
        if not isinstance(raw, str):
            continue
        s = raw.strip()
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        if s.startswith("[[") and s.endswith("]]"):
            s = s[2:-2]
        if s:
            out.append(s)
    # Also pull from input.notation if present.
    inp = fm.get("input")
    if isinstance(inp, dict):
        for raw in inp.get("notation", []) or []:
            if not isinstance(raw, str):
                continue
            s = raw.strip()
            if s.startswith('"') and s.endswith('"'):
                s = s[1:-1]
            if s.startswith("[[") and s.endswith("]]"):
                s = s[2:-2]
            if s:
                out.append(s)
    return out


# Heuristic symbol-to-notation mapping. Each entry: (regex, notation-stem).
# Tuned to the symbols listed in `_meta/_catalog-notation.md`. Heuristic by
# design, hence V2 is a warning-only check.
SYMBOL_HEURISTICS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\\bar\\Lambda_\{\\max\}\^\{\\dagger\}"), "notation--Lambda-bar-dagger"),
    (re.compile(r"\\kappa_j\^\{\\mathrm\{RSC\}\}"), "notation--kappa-RSC"),
    (re.compile(r"\\theta_1"), "notation--theta-1"),
    (re.compile(r"\\lambda_T"), "notation--lambda-T"),
    (re.compile(r"\\bm\{a\}"), "notation--bm-a"),
    (re.compile(r"\\bm\{N\}"), "notation--bm-N"),
    (re.compile(r"\\bm\{\\psi\}"), "notation--psi-basis"),
    (re.compile(r"\\Psi_\{k, ?m\}"), "notation--Psi-k-m"),
    (re.compile(r"\\Psi_k"), "notation--Psi-k"),
    (re.compile(r"\\alpha_j"), "notation--alpha-j"),
    (re.compile(r"\\phi'_\{\\min\}"), "notation--phi-prime-min"),
    (re.compile(r"\\phi_\{\\min\}"), "notation--phi-min"),
    (re.compile(r"\\phi_j"), "notation--phi-j"),
    (re.compile(r"\\eta_j\^\\star"), "notation--eta-j-star"),
    (re.compile(r"\\eta_j\("), "notation--eta-j-pred"),
    (re.compile(r"\\mu_j\^\\star"), "notation--mu-j-star"),
    (re.compile(r"\\lambda_j"), "notation--lambda-j-star"),
    (re.compile(r"\\omega_\{k, ?j\}\^\\star"), "notation--omega-kj-star"),
    (re.compile(r"\\omega_\{k, ?j\}"), "notation--omega-kj"),
    (re.compile(r"\\widehat\{\\bm\{s\}\}_j|\\widehat\{\\bm\{\\beta\}\}_\{k, ?j\}"), "notation--beta-hat-j"),
    (re.compile(r"\\widetilde\{\\bm\{\\beta\}\}_\{k, ?j\}"), "notation--beta-tilde-kj"),
    (re.compile(r"\\bm\{\\beta\}_\{k, ?j\}\^\\star"), "notation--beta-kj-star"),
    (re.compile(r"\\beta_\{k, ?j, ?m\}\^\\star"), "notation--beta-kjm-star"),
    (re.compile(r"\\bm\{s\}_j\^\\star"), "notation--s-j-star"),
    (re.compile(r"\\bm\{N\}|\bN_j\b"), "notation--N-j"),
    (re.compile(r"V_j(?![a-zA-Z])"), "notation--V-j"),
    (re.compile(r"B_j(?![a-zA-Z])"), "notation--B-j"),
    (re.compile(r"b_\{k, ?m\}\(T\)"), "notation--b-km-T"),
    (re.compile(r"T_0"), "notation--T-0"),
    (re.compile(r"\\log\s*p|\\log\(p\)"), "notation--log-p"),
    # Single-letter symbols are intentionally last and gated to avoid noise.
    (re.compile(r"\bQ\b(?![A-Za-z0-9_])"), "notation--Q"),
    (re.compile(r"\bM\b(?![A-Za-z0-9_])"), "notation--M"),
]


# ---------------------------------------------------------------------------
# Vault loader
# ---------------------------------------------------------------------------


class TheoryVault:
    """Loads the vault and indexes files by stem/kind/label."""

    def __init__(self, vault_root: Path, manuscript_root: Path):
        self.vault_root = vault_root
        self.manuscript_root = manuscript_root
        self.files: Dict[str, VaultFile] = {}  # stem -> VaultFile
        self.files_by_subdir: Dict[str, List[VaultFile]] = collections.defaultdict(list)
        self.files_by_kind: Dict[str, List[VaultFile]] = collections.defaultdict(list)
        self._load()

    def _load(self) -> None:
        for sub in SUBDIRS:
            d = self.vault_root / sub
            if not d.exists():
                continue
            for f in sorted(d.glob("*.md")):
                vf = parse_file(f, self.vault_root)
                if vf.stem in self.files:
                    # Duplicate stem across subdirs - unlikely but flag later.
                    pass
                self.files[vf.stem] = vf
                self.files_by_subdir[sub].append(vf)
                kind = (vf.fm.get("kind") if isinstance(vf.fm, dict) else None) or "unknown"
                self.files_by_kind[kind].append(vf)

    def has_stem(self, stem: str) -> bool:
        return stem in self.files

    def file_counts_by_kind(self) -> Dict[str, int]:
        return {k: len(v) for k, v in sorted(self.files_by_kind.items())}

    def all_files(self) -> Iterable[VaultFile]:
        return self.files.values()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_V1(vault: TheoryVault) -> List[Finding]:
    """Define-before-use: each [[wiki-link]] target must exist in the vault."""
    findings: List[Finding] = []
    valid_stems = set(vault.files.keys())
    for vf in vault.all_files():
        seen_per_target: Set[str] = set()
        for target, line_no in extract_wikilinks(vf.body):
            stem = _normalize_label_ref(target)
            if not stem or stem in seen_per_target:
                continue
            seen_per_target.add(stem)
            # Skip references that are clearly inline math labels (have spaces, $, etc.)
            if "$" in stem or " " in stem or "::" in stem:
                # Vault filenames use no `::`; manuscript labels like `thm::generic_main`
                # appearing inside `[[...]]` aren't vault refs.
                continue
            if stem not in valid_stems:
                findings.append(
                    Finding(
                        check_id="V1",
                        severity=DEFAULT_SEVERITY["V1"],
                        file=vf.rel_path,
                        line=line_no,
                        message=f"wiki-link target `{stem}` not found in vault",
                    )
                )
    return findings


def check_V2(vault: TheoryVault) -> List[Finding]:
    """Body-symbol scan: math symbols in body should appear in uses-notation."""
    findings: List[Finding] = []
    target_kinds = STATEMENT_KINDS | PROOF_KINDS
    for vf in vault.all_files():
        kind = vf.fm.get("kind")
        if kind not in target_kinds:
            continue
        declared = set(_get_uses_notation(vf.fm))
        reported: Set[str] = set()
        for pat, notation_stem in SYMBOL_HEURISTICS:
            if pat.search(vf.body):
                if notation_stem in declared:
                    continue
                if notation_stem in reported:
                    continue
                if not vault.has_stem(notation_stem):
                    continue  # silent - notation file itself missing
                reported.add(notation_stem)
                findings.append(
                    Finding(
                        check_id="V2",
                        severity=DEFAULT_SEVERITY["V2"],
                        file=vf.rel_path,
                        message=(
                            f"symbol pattern for `{notation_stem}` appears in body "
                            f"but `{notation_stem}` is not in uses-notation"
                        ),
                    )
                )
    return findings


def _find_proof_for_statement(vault: TheoryVault, vf: VaultFile) -> Optional[VaultFile]:
    raw = vf.fm.get("proof-file")
    if raw is None:
        return None
    stem = raw
    if isinstance(stem, str):
        stem = _normalize_label_ref(stem)
    if not isinstance(stem, str) or not stem:
        return None
    return vault.files.get(stem)


def _find_statement_for_proof(vault: TheoryVault, vf: VaultFile) -> Optional[VaultFile]:
    raw = vf.fm.get("statement-file")
    if raw is None:
        return None
    stem = raw
    if isinstance(stem, str):
        stem = _normalize_label_ref(stem)
    if not isinstance(stem, str) or not stem:
        return None
    return vault.files.get(stem)


def check_V3(vault: TheoryVault) -> List[Finding]:
    """Proof uses-assumptions must be subset of statement input.assumptions."""
    findings: List[Finding] = []
    for vf in vault.all_files():
        if vf.fm.get("kind") not in STATEMENT_KINDS:
            continue
        proof_vf = _find_proof_for_statement(vault, vf)
        if proof_vf is None:
            continue
        declared = set(_get_input_assumptions(vf.fm))
        used = set(_get_uses_assumptions(proof_vf.fm))
        if not declared and not used:
            continue
        extra = used - declared
        if extra:
            for label in sorted(extra):
                findings.append(
                    Finding(
                        check_id="V3",
                        severity=DEFAULT_SEVERITY["V3"],
                        file=proof_vf.rel_path,
                        message=(
                            f"proof invokes assumption `{label}` not declared "
                            f"in statement `{vf.rel_path}`"
                        ),
                    )
                )
    return findings


def check_V4(vault: TheoryVault) -> List[Finding]:
    """Transitive assumption tracking.

    Walks lemma dependencies of theorem proofs and collects all assumptions
    that appear in proof frontmatters along the way; reports anything not
    declared at the theorem statement.
    """
    findings: List[Finding] = []

    def closure(start_stem: str) -> Set[str]:
        seen_proofs: Set[str] = set()
        stack = [start_stem]
        acc: Set[str] = set()
        while stack:
            cur = stack.pop()
            if cur in seen_proofs:
                continue
            seen_proofs.add(cur)
            pf = vault.files.get(cur)
            if pf is None:
                continue
            acc.update(_get_uses_assumptions(pf.fm))
            for child in _get_uses_lemmas(pf.fm):
                # The wiki-link targets lemma *statements*; map to their proofs.
                child_stem = _normalize_label_ref(child)
                child_vf = vault.files.get(child_stem)
                if child_vf is None:
                    continue
                if child_vf.fm.get("kind") in STATEMENT_KINDS:
                    proof_vf = _find_proof_for_statement(vault, child_vf)
                    if proof_vf is not None:
                        stack.append(proof_vf.stem)
                elif child_vf.fm.get("kind") in PROOF_KINDS:
                    stack.append(child_vf.stem)
        return acc

    for vf in vault.all_files():
        if vf.fm.get("kind") != "theorem-statement":
            continue
        proof_vf = _find_proof_for_statement(vault, vf)
        if proof_vf is None:
            continue
        declared = set(_get_input_assumptions(vf.fm))
        all_used = closure(proof_vf.stem)
        missing = all_used - declared
        for label in sorted(missing):
            findings.append(
                Finding(
                    check_id="V4",
                    severity=DEFAULT_SEVERITY["V4"],
                    file=vf.rel_path,
                    message=(
                        f"transitive assumption `{label}` (reached via proof chain) "
                        f"is not declared in theorem statement"
                    ),
                )
            )
    return findings


def _extract_symbol(s) -> Optional[str]:
    if not isinstance(s, str):
        return None
    s = s.strip()
    # Strip leading bracketed annotations.
    s = re.sub(r"^\[[^\]]+\]\s*", "", s)
    if not s:
        return None
    return s


def check_V5(vault: TheoryVault) -> List[Finding]:
    """Symbol-clash: two notation files declaring the same `symbol` field."""
    findings: List[Finding] = []
    seen: Dict[str, List[str]] = collections.defaultdict(list)
    for vf in vault.files_by_subdir.get("notation", []):
        sym = vf.fm.get("symbol") or vf.fm.get("defines-symbol")
        sym = _extract_symbol(sym)
        if sym:
            seen[sym].append(vf.rel_path)
    for sym, paths in seen.items():
        if len(paths) > 1:
            for p in paths:
                findings.append(
                    Finding(
                        check_id="V5",
                        severity=DEFAULT_SEVERITY["V5"],
                        file=p,
                        message=f"symbol `{sym}` is declared in multiple notation files: "
                        + ", ".join(paths),
                    )
                )
    return findings


def check_V6(vault: TheoryVault) -> List[Finding]:
    """Orphan-lemma detection: lemma statement files not referenced anywhere."""
    findings: List[Finding] = []
    # Build a reverse index: which stems are referenced from any file?
    refs: Set[str] = set()
    for vf in vault.all_files():
        # Wiki-links in body.
        for target, _ in extract_wikilinks(vf.body):
            refs.add(_normalize_label_ref(target))
        # Wiki-link-shaped frontmatter values.
        for key in ("uses-lemmas", "uses-definitions", "uses-notation",
                    "follows-from", "attached-to", "statement-file",
                    "proof-file"):
            raw = vf.fm.get(key)
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, str):
                        refs.add(_normalize_label_ref(item))
            elif isinstance(raw, str):
                refs.add(_normalize_label_ref(raw))
        # input.definitions / input.notation / events
        inp = vf.fm.get("input")
        if isinstance(inp, dict):
            for sub_key in ("definitions", "notation"):
                for item in inp.get(sub_key, []) or []:
                    if isinstance(item, str):
                        refs.add(_normalize_label_ref(item))
        for item in vf.fm.get("events", []) or []:
            if isinstance(item, str):
                refs.add(_normalize_label_ref(item))

    for vf in vault.files_by_subdir.get("lemmas", []):
        if vf.fm.get("kind") != "lemma-statement":
            continue
        used_by = vf.fm.get("used-by") or []
        has_used_by = bool(used_by) if isinstance(used_by, list) else bool(str(used_by).strip())
        if has_used_by:
            continue
        if vf.stem in refs:
            continue
        findings.append(
            Finding(
                check_id="V6",
                severity=DEFAULT_SEVERITY["V6"],
                file=vf.rel_path,
                message="lemma has empty `used-by:` and is not referenced anywhere in the vault",
            )
        )
    return findings


def check_V7(vault: TheoryVault) -> List[Finding]:
    """Missing-proof: statement-file's `proof-file:` must exist (unless null).

    Exception: corollary statements with `proof-file: null` (no proof block).
    """
    findings: List[Finding] = []
    for vf in vault.all_files():
        kind = vf.fm.get("kind")
        if kind not in STATEMENT_KINDS:
            continue
        raw = vf.fm.get("proof-file")
        if raw is None:
            # Corollaries permit null; theorems/lemmas should not.
            if kind == "corollary-statement":
                continue
            findings.append(
                Finding(
                    check_id="V7",
                    severity=DEFAULT_SEVERITY["V7"],
                    file=vf.rel_path,
                    message=f"{kind} has `proof-file: null` (expected a proof file)",
                )
            )
            continue
        if not isinstance(raw, str):
            findings.append(
                Finding(
                    check_id="V7",
                    severity=DEFAULT_SEVERITY["V7"],
                    file=vf.rel_path,
                    message=f"`proof-file:` value `{raw!r}` is not a string",
                )
            )
            continue
        stem = _normalize_label_ref(raw)
        if not vault.has_stem(stem):
            findings.append(
                Finding(
                    check_id="V7",
                    severity=DEFAULT_SEVERITY["V7"],
                    file=vf.rel_path,
                    message=f"`proof-file: {stem}` references a non-existent vault entry",
                )
            )
    return findings


def check_V8(vault: TheoryVault) -> List[Finding]:
    """Citation-chain inventory. Warning-level: reports unique bibkeys."""
    findings: List[Finding] = []
    all_keys: Set[str] = set()
    per_file: Dict[str, Set[str]] = {}
    for vf in vault.all_files():
        keys = extract_bibkeys(vf.body)
        if keys:
            per_file[vf.rel_path] = keys
            all_keys |= keys
    # Emit one summary finding plus one per-file finding for visibility.
    if all_keys:
        findings.append(
            Finding(
                check_id="V8",
                severity=DEFAULT_SEVERITY["V8"],
                file="(vault)",
                message=(
                    f"{len(all_keys)} unique bibkeys cited across "
                    f"{len(per_file)} files: "
                    + ", ".join(sorted(all_keys))
                ),
            )
        )
    return findings


_LABEL_RE_CACHE: Dict[str, Set[str]] = {}


def _labels_in_tex(path: Path) -> Set[str]:
    key = str(path)
    if key in _LABEL_RE_CACHE:
        return _LABEL_RE_CACHE[key]
    if not path.exists():
        _LABEL_RE_CACHE[key] = set()
        return _LABEL_RE_CACHE[key]
    text = path.read_text(encoding="utf-8", errors="replace")
    labels = set(re.findall(r"\\label\{([^}]+)\}", text))
    _LABEL_RE_CACHE[key] = labels
    return labels


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


MANUSCRIPT_ANCHOR_RE = re.compile(r"^([^:]+):(.+)$")


def _resolve_manuscript_path(rel_tex: str, manuscript_root: Path) -> Path:
    """Resolve a vault `manuscript-anchor` file portion under the supplied
    manuscript root, tolerating a leading `src/main/` segment that vault
    files retain for legacy reasons.
    """
    candidate = manuscript_root / rel_tex
    if candidate.exists():
        return candidate
    if rel_tex.startswith(MANUSCRIPT_PATH_PREFIX_STRIP):
        stripped = rel_tex[len(MANUSCRIPT_PATH_PREFIX_STRIP):]
        alt = manuscript_root / stripped
        if alt.exists():
            return alt
        return alt
    return candidate


def check_V9(vault: TheoryVault, manuscript_root: Path) -> List[Finding]:
    """Manuscript-anchor drift detection."""
    findings: List[Finding] = []
    for vf in vault.all_files():
        raw = vf.fm.get("manuscript-anchor")
        if raw is None:
            continue
        if not isinstance(raw, str):
            continue
        if raw.strip().lower() == "null":
            continue
        m = MANUSCRIPT_ANCHOR_RE.match(raw.strip())
        if not m:
            findings.append(
                Finding(
                    check_id="V9",
                    severity=DEFAULT_SEVERITY["V9"],
                    file=vf.rel_path,
                    message=f"unparseable manuscript-anchor: `{raw}`",
                )
            )
            continue
        rel_tex, locator = m.group(1).strip(), m.group(2).strip()
        tex_path = _resolve_manuscript_path(rel_tex, manuscript_root)
        if not tex_path.exists():
            findings.append(
                Finding(
                    check_id="V9",
                    severity=DEFAULT_SEVERITY["V9"],
                    file=vf.rel_path,
                    message=f"manuscript file `{rel_tex}` does not exist",
                )
            )
            continue
        # Locator can be a line number, a range `a-b`, or a label (contains :: or alpha).
        if re.match(r"^\d+(?:-\d+)?$", locator):
            # Line / line-range
            first_n = int(locator.split("-")[0])
            lc = _line_count(tex_path)
            if first_n > lc:
                findings.append(
                    Finding(
                        check_id="V9",
                        severity=DEFAULT_SEVERITY["V9"],
                        file=vf.rel_path,
                        message=(
                            f"manuscript-anchor line {first_n} exceeds file length "
                            f"{lc} of `{rel_tex}`"
                        ),
                    )
                )
        else:
            # Treat as label.
            labels = _labels_in_tex(tex_path)
            if locator not in labels:
                findings.append(
                    Finding(
                        check_id="V9",
                        severity=DEFAULT_SEVERITY["V9"],
                        file=vf.rel_path,
                        message=(
                            f"manuscript-anchor label `{locator}` not found in "
                            f"`{rel_tex}`"
                        ),
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# Manuscript scan utilities for V10-V14
# ---------------------------------------------------------------------------


MANUSCRIPT_LABEL_KIND_RE = re.compile(
    r"\\label\{("
    + "|".join(MANUSCRIPT_LABEL_KINDS)
    + r")::([^}]+)\}"
)
BEGIN_ENV_RE = re.compile(r"\\begin\{([A-Za-z*]+)\}")
END_ENV_RE = re.compile(r"\\end\{([A-Za-z*]+)\}")
ANY_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
# Manuscript-side reference forms that we treat as "the label is referenced".
REF_FORMS = ("ref", "eqref", "cref", "Cref", "autoref", "ref*")


def _iter_manuscript_tex_files(manuscript_root: Path) -> List[Path]:
    out: List[Path] = []
    for sub in ("sections", "appendices"):
        d = manuscript_root / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.tex")):
            out.append(f)
    return out


_MANUSCRIPT_TEXT_CACHE: Dict[str, str] = {}


def _read_manuscript(path: Path) -> str:
    key = str(path)
    if key in _MANUSCRIPT_TEXT_CACHE:
        return _MANUSCRIPT_TEXT_CACHE[key]
    if not path.exists():
        _MANUSCRIPT_TEXT_CACHE[key] = ""
        return ""
    _MANUSCRIPT_TEXT_CACHE[key] = path.read_text(encoding="utf-8", errors="replace")
    return _MANUSCRIPT_TEXT_CACHE[key]


def _collect_manuscript_labels(
    manuscript_root: Path,
) -> Dict[str, Tuple[Path, int]]:
    """Return mapping label -> (tex_path, 1-based line number of `\\label{...}`)
    for every target-kind label found under `sections/` and `appendices/`.

    When the same label appears more than once, the first occurrence wins.
    """
    out: Dict[str, Tuple[Path, int]] = {}
    for tex_path in _iter_manuscript_tex_files(manuscript_root):
        text = _read_manuscript(tex_path)
        for line_idx, line in enumerate(text.splitlines(), start=1):
            for m in MANUSCRIPT_LABEL_KIND_RE.finditer(line):
                kind, suffix = m.group(1), m.group(2)
                label = f"{kind}::{suffix}"
                if label not in out:
                    out[label] = (tex_path, line_idx)
    return out


def _find_labeled_environment_block(
    text: str, target_label: str
) -> Optional[Tuple[int, int, str, str]]:
    """Locate a `\\begin{env} ... \\label{target_label} ... \\end{env}` block.

    The `\\label{}` may sit on the `\\begin{}` line, on a later line inside
    the body, or on the trailing portion of the same line as `\\end{}` --
    LaTeX is lenient. We scan environments by matching balanced
    `\\begin{...}` / `\\end{...}` (same env name) and accept the first
    environment whose body contains `\\label{target_label}`.

    Returns (body_start_line, body_end_line, env_name, body_text) on a hit,
    where body_start_line is the line immediately after `\\begin{env}` and
    body_end_line is the line immediately before `\\end{env}` (both 1-based).
    The body_text excludes the `\\begin{}` and `\\end{}` lines.
    """
    lines = text.splitlines()
    n = len(lines)
    stack: List[Tuple[str, int]] = []
    for i, line in enumerate(lines):
        for bm in BEGIN_ENV_RE.finditer(line):
            stack.append((bm.group(1), i))
        for em in END_ENV_RE.finditer(line):
            env = em.group(1)
            # Pop the most recent matching begin.
            popped: Optional[Tuple[str, int]] = None
            for k in range(len(stack) - 1, -1, -1):
                if stack[k][0] == env:
                    popped = stack[k]
                    del stack[k]
                    break
            if popped is None:
                continue
            begin_line = popped[1]
            block_text = "\n".join(lines[begin_line: i + 1])
            if f"\\label{{{target_label}}}" in block_text:
                body = "\n".join(lines[begin_line + 1: i])
                return (begin_line + 2, i, env, body)
    return None


# ---------------------------------------------------------------------------
# Vault body utilities for V10-V14
# ---------------------------------------------------------------------------


FENCED_BLOCK_RE = re.compile(
    r"```(?:[A-Za-z]*)\s*\n(.*?)\n```",
    re.DOTALL,
)


def _extract_vault_verbatim_block(body: str, target_label: str) -> Optional[str]:
    """Return the body of the first fenced code block whose content
    contains `\\label{target_label}`. The body excludes the fence lines and
    excludes the leading `\\begin{env}` line and the trailing `\\end{env}`
    line, so it matches the manuscript-side body extracted by
    `_find_labeled_environment_block`.
    """
    for m in FENCED_BLOCK_RE.finditer(body):
        block = m.group(1)
        if f"\\label{{{target_label}}}" not in block:
            continue
        block_lines = block.splitlines()
        # Find the begin/end lines.
        begin_idx: Optional[int] = None
        end_idx: Optional[int] = None
        for j, line in enumerate(block_lines):
            if BEGIN_ENV_RE.search(line) and begin_idx is None:
                begin_idx = j
            if END_ENV_RE.search(line):
                end_idx = j
        if begin_idx is None or end_idx is None or end_idx <= begin_idx:
            # No begin/end pair detected; treat whole block as the body.
            return "\n".join(block_lines)
        return "\n".join(block_lines[begin_idx + 1: end_idx])
    return None


# V11 normalisation: spacing-command tokens that should compare equal.
# Order matters: multi-character commands (e.g. `\quad`, `\qquad`,
# `\thinspace`) must be substituted before single-character commands
# (`\,`, `\!`, etc.) to avoid partial matches. We replace each with the
# same canonical sentinel so different spacing/punctuation commands
# compare equal under V11.
_SPACING_COMMAND_TOKEN = "␣"  # `␣` open-box; will be collapsed with surrounding whitespace
_SPACING_COMMAND_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\\qquad(?![A-Za-z])"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\quad(?![A-Za-z])"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\thinspace(?![A-Za-z])"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\medspace(?![A-Za-z])"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\thickspace(?![A-Za-z])"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\cdot(?![A-Za-z])"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\,"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\!"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\:"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\;"), _SPACING_COMMAND_TOKEN),
    (re.compile(r"\\ "), _SPACING_COMMAND_TOKEN),
]


def _strip_latex_comments(line: str) -> Optional[str]:
    """Strip LaTeX comments from a line.

    - If the first non-whitespace character is `%`, the entire line is a
      comment; return None so the caller can drop it.
    - Otherwise strip any mid-line `%`-to-end-of-line comment. A `%`
      preceded by an odd number of backslashes is an escaped percent and
      is kept (`\\%`). Returns the (possibly trimmed) line text.
    """
    stripped = line.lstrip()
    if stripped.startswith("%"):
        return None
    # Find first unescaped `%`.
    i = 0
    while i < len(line):
        if line[i] == "%":
            # Count backslashes immediately preceding.
            k = 0
            j = i - 1
            while j >= 0 and line[j] == "\\":
                k += 1
                j -= 1
            if k % 2 == 0:
                # Unescaped: this and everything after is a comment.
                return line[:i]
        i += 1
    return line


def _normalize_for_compare(text: str) -> str:
    """Normalise a manuscript / vault body for V11 comparison.

    Applies, in order:
      1. Strip LaTeX comment lines (lines whose first non-whitespace
         char is `%`) entirely; strip mid-line `%`-to-EOL comments on
         remaining lines.
      2. Map spacing/punctuation commands (`\\,`, `\\!`, `\\:`, `\\;`,
         `\\ `, `\\quad`, `\\qquad`, `\\cdot`, `\\thinspace`,
         `\\medspace`, `\\thickspace`) to a single canonical token so
         different spacing choices compare equal.
      3. Collapse all whitespace runs within a line to a single space
         and trim leading/trailing whitespace; drop fully blank lines.
      4. Case is preserved (theorem names and symbol identifiers are
         case-sensitive).
    """
    out_lines: List[str] = []
    for raw_line in text.splitlines():
        stripped = _strip_latex_comments(raw_line)
        if stripped is None:
            continue
        ln = stripped
        for pat, token in _SPACING_COMMAND_PATTERNS:
            ln = pat.sub(token, ln)
        # Collapse whitespace runs (including those adjacent to the
        # spacing-command token) into a single token. This makes
        # `}\, \|` and `} \qquad \|` and `}\qquad\|` all compare equal
        # by funnelling every contiguous whitespace-or-spacing-token
        # group down to a single canonical token.
        ln = re.sub(
            r"(?:\s*" + re.escape(_SPACING_COMMAND_TOKEN) + r"\s*)+",
            _SPACING_COMMAND_TOKEN,
            ln,
        )
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln:
            continue
        out_lines.append(ln)
    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# V10: every manuscript label of a target kind has a vault node
# ---------------------------------------------------------------------------


def check_V10(vault: TheoryVault, manuscript_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    labels = _collect_manuscript_labels(manuscript_root)
    # Build vault label -> file index over active files. Deprecated files do
    # not satisfy V10 (a manuscript label must have a live canonical node).
    label_to_files: Dict[str, List[VaultFile]] = collections.defaultdict(list)
    for vf in vault.all_files():
        lab = vf.fm.get("label")
        if not isinstance(lab, str):
            continue
        if vf.fm.get("status") == "deprecated":
            continue
        label_to_files[lab.strip()].append(vf)
    for label, (tex_path, line_no) in sorted(labels.items()):
        if label not in label_to_files:
            try:
                rel_tex = tex_path.relative_to(manuscript_root).as_posix()
            except ValueError:
                rel_tex = str(tex_path)
            findings.append(
                Finding(
                    check_id="V10",
                    severity=DEFAULT_SEVERITY["V10"],
                    file=f"(manuscript)/{rel_tex}",
                    line=line_no,
                    message=(
                        f"manuscript `\\label{{{label}}}` has no active vault file "
                        f"with `label: {label}`"
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# V11: vault verbatim block matches the manuscript at the cited label
# ---------------------------------------------------------------------------


def check_V11(vault: TheoryVault, manuscript_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for vf in vault.all_files():
        raw = vf.fm.get("manuscript-anchor")
        if not isinstance(raw, str):
            continue
        raw = raw.strip()
        if not raw or raw.lower() == "null":
            continue
        m = MANUSCRIPT_ANCHOR_RE.match(raw)
        if not m:
            continue
        rel_tex, locator = m.group(1).strip(), m.group(2).strip()
        # Symbolic-form locator only; line-number-form anchors are V14's job.
        if re.match(r"^\d+(?:-\d+)?$", locator):
            continue
        tex_path = _resolve_manuscript_path(rel_tex, manuscript_root)
        if not tex_path.exists():
            continue  # V9 already reports the missing manuscript file
        # Restrict V11 to labels of target kinds; other locators (e.g.
        # `sec::xxx`, `app::xxx`) point to sectioning anchors with no
        # `\begin{...}\end{...}` block to compare against.
        kind_prefix = locator.split("::", 1)[0] if "::" in locator else ""
        if kind_prefix not in MANUSCRIPT_LABEL_KINDS:
            continue
        text = _read_manuscript(tex_path)
        block = _find_labeled_environment_block(text, locator)
        if block is None:
            findings.append(
                Finding(
                    check_id="V11",
                    severity=DEFAULT_SEVERITY["V11"],
                    file=vf.rel_path,
                    message=(
                        f"no `\\begin{{...}}\\label{{{locator}}}\\end{{...}}` "
                        f"block found in `{rel_tex}` to compare against"
                    ),
                )
            )
            continue
        _, _, _, ms_body = block
        vault_body = _extract_vault_verbatim_block(vf.body, locator)
        if vault_body is None:
            findings.append(
                Finding(
                    check_id="V11",
                    severity=DEFAULT_SEVERITY["V11"],
                    file=vf.rel_path,
                    message=(
                        f"no fenced verbatim block containing "
                        f"`\\label{{{locator}}}` found in vault body"
                    ),
                )
            )
            continue
        if _normalize_for_compare(ms_body) != _normalize_for_compare(vault_body):
            findings.append(
                Finding(
                    check_id="V11",
                    severity=DEFAULT_SEVERITY["V11"],
                    file=vf.rel_path,
                    message=(
                        f"vault verbatim body for `{locator}` differs from "
                        f"manuscript block in `{rel_tex}`"
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# V12: every vault label of a target kind is referenced in the manuscript
# ---------------------------------------------------------------------------


def _collect_manuscript_references(manuscript_root: Path) -> Set[str]:
    """Return the set of all label-tokens that appear in the manuscript via
    `\\ref`, `\\eqref`, `\\cref`, `\\Cref`, `\\autoref`, `\\ref*`, or
    `\\label`."""
    refs: Set[str] = set()
    ref_re = re.compile(
        r"\\(?:" + "|".join(re.escape(r) for r in REF_FORMS) + r"|label)\{([^}]+)\}"
    )
    for tex_path in _iter_manuscript_tex_files(manuscript_root):
        text = _read_manuscript(tex_path)
        for m in ref_re.finditer(text):
            # `\ref{a,b,c}` is legal under cleveref; split on commas.
            for tok in m.group(1).split(","):
                tok = tok.strip()
                if tok:
                    refs.add(tok)
    return refs


def check_V12(vault: TheoryVault, manuscript_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    refs = _collect_manuscript_references(manuscript_root)
    # Proof-companion and case-study files carry vault-internal labels (e.g.
    # `lmm::xxx-proof`, `case::xxx`) that intentionally have no manuscript
    # counterpart. They are exempt from V12.
    vault_internal_kinds = PROOF_KINDS | {"case-study"}
    for vf in vault.all_files():
        if vf.fm.get("status") == "deprecated":
            continue
        if vf.fm.get("kind") in vault_internal_kinds:
            continue
        lab = vf.fm.get("label")
        if not isinstance(lab, str):
            continue
        lab = lab.strip()
        if "::" not in lab:
            continue
        kind_prefix = lab.split("::", 1)[0]
        if kind_prefix not in MANUSCRIPT_LABEL_KINDS:
            continue
        if lab not in refs:
            findings.append(
                Finding(
                    check_id="V12",
                    severity=DEFAULT_SEVERITY["V12"],
                    file=vf.rel_path,
                    message=(
                        f"vault label `{lab}` is not referenced anywhere in the "
                        f"manuscript"
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# V13: wikilink targets resolve as exact basenames under theory/
# ---------------------------------------------------------------------------


def _collect_vault_basenames(vault_root: Path) -> Set[str]:
    """Return the set of `.md` file stems found anywhere under `theory/`,
    excluding `_archive/`, `_meta/`, `_scripts/`."""
    out: Set[str] = set()
    for p in vault_root.rglob("*.md"):
        rel = p.relative_to(vault_root).as_posix()
        first = rel.split("/", 1)[0]
        if first in ("_archive", "_meta", "_scripts"):
            continue
        out.add(p.stem)
    return out


def check_V13(vault: TheoryVault) -> List[Finding]:
    findings: List[Finding] = []
    basenames = _collect_vault_basenames(vault.vault_root)
    for vf in vault.all_files():
        seen_per_target: Set[str] = set()
        for target, line_no in extract_wikilinks(vf.body):
            stem = _normalize_label_ref(target)
            if not stem or stem in seen_per_target:
                continue
            seen_per_target.add(stem)
            # Skip non-basename wikilinks (V1 already handles vault-stem refs).
            if "$" in stem or " " in stem or "::" in stem:
                continue
            if stem not in basenames:
                findings.append(
                    Finding(
                        check_id="V13",
                        severity=DEFAULT_SEVERITY["V13"],
                        file=vf.rel_path,
                        line=line_no,
                        message=(
                            f"wikilink `[[{stem}]]` does not match any `*.md` "
                            f"basename under `theory/` (excluding archive)"
                        ),
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# V14: stale manuscript-anchor line numbers (legacy line-form, manuscript-label)
# ---------------------------------------------------------------------------


def check_V14(vault: TheoryVault, manuscript_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    manuscript_labels = _collect_manuscript_labels(manuscript_root)
    for vf in vault.all_files():
        raw = vf.fm.get("manuscript-anchor")
        if not isinstance(raw, str):
            continue
        raw = raw.strip()
        if not raw or raw.lower() == "null":
            continue
        m = MANUSCRIPT_ANCHOR_RE.match(raw)
        if not m:
            continue
        rel_tex, locator = m.group(1).strip(), m.group(2).strip()
        if not re.match(r"^\d+(?:-\d+)?$", locator):
            continue
        # Only enforce V14 on files whose `label:` corresponds to a
        # manuscript `\label{}` of the target kinds. Vault-internal labels
        # (notation::*, lmm::*-proof, etc.) are exempt: their anchor is a
        # line number by design because no manuscript label exists.
        lab = vf.fm.get("label")
        if not isinstance(lab, str):
            continue
        lab = lab.strip()
        if lab not in manuscript_labels:
            continue
        tex_path = _resolve_manuscript_path(rel_tex, manuscript_root)
        if not tex_path.exists():
            continue  # V9 reports
        first_n = int(locator.split("-")[0])
        ms_path, ms_line = manuscript_labels[lab]
        # Compare line numbers; tolerate +/- 2 lines because some manuscript
        # labels sit one line below the `\begin{}` (e.g. asmp::spectralradius).
        if abs(first_n - ms_line) > 2:
            try:
                rel_actual = ms_path.relative_to(manuscript_root).as_posix()
            except ValueError:
                rel_actual = str(ms_path)
            findings.append(
                Finding(
                    check_id="V14",
                    severity=DEFAULT_SEVERITY["V14"],
                    file=vf.rel_path,
                    message=(
                        f"manuscript-anchor line {first_n} does not match "
                        f"manuscript `\\label{{{lab}}}` at line {ms_line} "
                        f"of `{rel_actual}`"
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _check_sort_key(check_id: str) -> int:
    """Numeric sort key for check ids like `V1`, `V10`, so the report
    orders V1..V14 by number rather than lexicographically."""
    m = re.match(r"^V(\d+)$", check_id)
    return int(m.group(1)) if m else 0


def load_severity_overrides(vault_root: Path) -> Dict[str, str]:
    cfg = vault_root / "_meta/verifier.yaml"
    if not cfg.exists() or not HAVE_YAML:
        return {}
    try:
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    sev = data.get("severity") if isinstance(data.get("severity"), dict) else data
    out = {}
    for k, v in sev.items():
        if k in DEFAULT_SEVERITY and v in ("error", "warning"):
            out[k] = v
    return out


def run_all_checks(
    vault: TheoryVault, manuscript_root: Path, selected: Optional[Set[str]] = None
) -> Dict[str, List[Finding]]:
    selected = selected or set(DEFAULT_SEVERITY.keys())
    results: Dict[str, List[Finding]] = {}
    if "V1" in selected:
        results["V1"] = check_V1(vault)
    if "V2" in selected:
        results["V2"] = check_V2(vault)
    if "V3" in selected:
        results["V3"] = check_V3(vault)
    if "V4" in selected:
        results["V4"] = check_V4(vault)
    if "V5" in selected:
        results["V5"] = check_V5(vault)
    if "V6" in selected:
        results["V6"] = check_V6(vault)
    if "V7" in selected:
        results["V7"] = check_V7(vault)
    if "V8" in selected:
        results["V8"] = check_V8(vault)
    if "V9" in selected:
        results["V9"] = check_V9(vault, manuscript_root)
    if "V10" in selected:
        results["V10"] = check_V10(vault, manuscript_root)
    if "V11" in selected:
        results["V11"] = check_V11(vault, manuscript_root)
    if "V12" in selected:
        results["V12"] = check_V12(vault, manuscript_root)
    if "V13" in selected:
        results["V13"] = check_V13(vault)
    if "V14" in selected:
        results["V14"] = check_V14(vault, manuscript_root)
    return results


def write_report(
    vault: TheoryVault,
    findings_by_check: Dict[str, List[Finding]],
    report_path: Path,
    severity_overrides: Dict[str, str],
    strict: bool,
) -> Tuple[int, int]:
    lines: List[str] = []
    lines.append("---")
    lines.append("kind: verifier-report")
    lines.append(f"vault-root: {vault.vault_root}")
    lines.append("generator: theory/_scripts/check_theory_graph.py")
    lines.append(f"strict-mode: {strict}")
    lines.append("---")
    lines.append("")
    lines.append("# Theory-vault verifier report")
    lines.append("")
    lines.append("## File inventory")
    lines.append("")
    counts = vault.file_counts_by_kind()
    total = sum(counts.values())
    lines.append(f"- Total files indexed: {total}")
    for kind, n in counts.items():
        lines.append(f"- `{kind}`: {n}")
    lines.append("")

    # Severity table
    lines.append("## Summary by check")
    lines.append("")
    lines.append("Check | Severity | Errors | Warnings | Title")
    lines.append("---|---|---|---|---")
    grand_err = 0
    grand_warn = 0
    for check_id in sorted(DEFAULT_SEVERITY.keys(), key=_check_sort_key):
        if check_id not in findings_by_check:
            continue
        sev_default = severity_overrides.get(check_id, DEFAULT_SEVERITY[check_id])
        n_err = sum(1 for f in findings_by_check[check_id] if f.severity == "error")
        n_warn = sum(1 for f in findings_by_check[check_id] if f.severity == "warning")
        grand_err += n_err
        grand_warn += n_warn
        lines.append(
            f"{check_id} | {sev_default} | {n_err} | {n_warn} | {CHECK_TITLES[check_id]}"
        )
    lines.append("")
    lines.append(f"**Total: errors={grand_err}, warnings={grand_warn}**")
    lines.append("")

    # Per-check details
    for check_id in sorted(DEFAULT_SEVERITY.keys(), key=_check_sort_key):
        if check_id not in findings_by_check:
            continue
        items = findings_by_check[check_id]
        lines.append(f"## {check_id} — {CHECK_TITLES[check_id]}")
        lines.append("")
        if not items:
            lines.append("_No findings._")
            lines.append("")
            continue
        errs = [f for f in items if f.severity == "error"]
        warns = [f for f in items if f.severity == "warning"]
        if errs:
            lines.append(f"### Errors ({len(errs)})")
            lines.append("")
            for f in errs:
                loc = f":line {f.line}" if f.line else ""
                lines.append(f"- `{f.file}`{loc}: {f.message}")
            lines.append("")
        if warns:
            lines.append(f"### Warnings ({len(warns)})")
            lines.append("")
            for f in warns:
                loc = f":line {f.line}" if f.line else ""
                lines.append(f"- `{f.file}`{loc}: {f.message}")
            lines.append("")

    # Top-10 highest-impact: files with most error-level findings.
    lines.append("## Top 10 highest-impact files (by error count)")
    lines.append("")
    file_err_counts: Dict[str, int] = collections.Counter()
    for items in findings_by_check.values():
        for f in items:
            if f.severity == "error":
                file_err_counts[f.file] += 1
    if not file_err_counts:
        lines.append("_No error-level findings; nothing to rank._")
        lines.append("")
    else:
        top = file_err_counts.most_common(10)
        lines.append("Rank | File | Error count")
        lines.append("---|---|---")
        for i, (path, n) in enumerate(top, start=1):
            lines.append(f"{i} | `{path}` | {n}")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return grand_err, grand_warn


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hawkes theory-vault verifier.")
    p.add_argument(
        "--vault",
        type=Path,
        default=DEFAULT_VAULT,
        help=f"Vault root (default: {DEFAULT_VAULT})",
    )
    p.add_argument(
        "--manuscript-root",
        type=Path,
        default=DEFAULT_MANUSCRIPT_ROOT,
        help=f"Manuscript root for V9 (default: {DEFAULT_MANUSCRIPT_ROOT})",
    )
    p.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Report destination (default: {DEFAULT_REPORT})",
    )
    p.add_argument(
        "--check",
        type=str,
        default="",
        help="Comma-separated subset of checks (e.g. V1,V3). Default: all.",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors for exit-code purposes.",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    _apply_vault_config(args.vault)
    vault = TheoryVault(args.vault, args.manuscript_root)
    severity_overrides = load_severity_overrides(args.vault)
    # Apply severity overrides in DEFAULT_SEVERITY dict for run.
    for k, v in severity_overrides.items():
        DEFAULT_SEVERITY[k] = v
    selected: Optional[Set[str]] = None
    if args.check.strip():
        selected = {c.strip() for c in args.check.split(",") if c.strip()}
        unknown = selected - set(DEFAULT_SEVERITY.keys())
        if unknown:
            print(f"Unknown check id(s): {sorted(unknown)}", file=sys.stderr)
            return 2
    findings = run_all_checks(vault, args.manuscript_root, selected=selected)
    n_err, n_warn = write_report(
        vault, findings, args.report_path, severity_overrides, args.strict
    )
    print(
        f"Verifier complete. files={sum(vault.file_counts_by_kind().values())} "
        f"errors={n_err} warnings={n_warn} report={args.report_path}"
    )
    if args.strict and (n_err + n_warn) > 0:
        return 1
    if n_err > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
