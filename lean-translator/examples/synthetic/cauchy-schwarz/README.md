# Synthetic example — Cauchy-Schwarz inequality

This is the skill's self-illustration. It demonstrates the full vault → Lean translation flow on the simplest possible non-trivial case: the Cauchy-Schwarz inequality in an inner product space, which Mathlib covers via one term application.

**Purpose:** validate the toolchain (Lake project shape, Mathlib dependency, frontmatter contract, statement-parity diff format) and serve as the worked example referenced from `roles/translator.md` and protocol example blocks. Contains no domain-specific or research-bound content.

## Layout

```
cauchy-schwarz/
├── README.md                                      (this file)
├── vault/
│   ├── _meta/config.yaml                          minimal project config
│   ├── theorems/CS_inner_product.md               vault statement
│   └── theorem-proofs/CS_inner_product.md         vault proof
└── lean/
    ├── lakefile.toml                              Mathlib-dependent Lake project
    ├── lean-toolchain                             pinned Lean 4 toolchain
    ├── lake-manifest.json                         dependency lock
    ├── SyntheticExample.lean                      root module (imports below)
    ├── SyntheticExample/
    │   ├── ProjectLib/Empty.lean                  project-local Lean (empty for this example)
    │   └── Translated/Theorems/CS_inner_product.lean   the canonical Lean translation
    ├── _meta/                                     reserved for triage CSV (unused here)
    └── _attempts/                                 reserved for failed-attempt diagnostics (unused here)
```

## Vault statement (informal)

Let $E$ be an inner product space over $\mathbb{K} \in \{\mathbb{R}, \mathbb{C}\}$ and $u, v \in E$. Then $|\langle u, v \rangle| \le \|u\| \cdot \|v\|$.

## Lean translation

```lean
theorem CS_inner_product (u v : E) :
    ‖inner 𝕜 u v‖ ≤ ‖u‖ * ‖v‖ :=
  norm_inner_le_norm u v
```

Provided in `Mathlib.Analysis.InnerProductSpace.Basic` (`norm_inner_le_norm`, around line 455).

## Build

```
cd lean/
lake build
```

First build on a fresh machine downloads Mathlib (~5 GB, takes 30–60 minutes depending on cache availability). Subsequent builds are incremental and fast.

`lake init synthetic_example math` was used to bootstrap; `lake exe cache get` fired automatically during init and populated `.lake/packages/mathlib/` from the leanprover-community Azure cache.

## How this example was authored (translator perspective)

The Stage 1–5 pipeline from `roles/translator.md` was followed manually:

- **Stage 1 (Lean statement only).** Wrote the theorem statement against `Mathlib.Analysis.InnerProductSpace.Basic`'s `InnerProductSpace` typeclass.
- **Stage 2 (proof body).** First attempt used `abs_inner_le_norm` (recalled name).
- **Stage 3 (compile-iterate).** First `lake build` failed: `Unknown identifier 'abs_inner_le_norm'`. Searched Mathlib source for the current name; found `norm_inner_le_norm` at `Mathlib/Analysis/InnerProductSpace/Basic.lean:455`. One iteration.
- **Stage 4 (success).** Build succeeded on iteration 2. In a real translator dispatch, vault frontmatter would flip to `verified-pending-review` here.
- **Stage 5 (failure).** Not exercised — example succeeded.

Total iterations: 2 (out of budget K=5). Typical for a Mathlib-covered theorem with a single-name lookup error.

## Statement-parity diff (what the human gate would see)

```
Vault statement:
  Let E be an inner product space over K ∈ {ℝ, ℂ}, u v ∈ E.
  Then |⟨u, v⟩| ≤ ‖u‖ · ‖v‖.

Lean statement:
  theorem CS_inner_product (u v : E) : ‖inner 𝕜 u v‖ ≤ ‖u‖ * ‖v‖

Notes:
  - K (informal) → 𝕜 (Mathlib's convention for the inner-product field)
  - ⟨u, v⟩ → inner 𝕜 u v (Mathlib syntax; the notation ⟪u, v⟫ also works)
  - |·| (absolute value) → ‖·‖ (norm, which coincides with absolute value on ℝ and ℂ)
  - · → * (multiplication)
  - Implicit: the theorem operates on any E with [NormedAddCommGroup E] [InnerProductSpace 𝕜 E]
    instances, which subsumes both finite-dim (e.g., EuclideanSpace ℝ (Fin n)) and infinite-dim
    cases.

Verdict: statement-parity APPROVED (the Lean statement faithfully captures the vault claim).
```

The user would type `approved`, and the vault frontmatter would flip from `verified-pending-review` to `verified`.
