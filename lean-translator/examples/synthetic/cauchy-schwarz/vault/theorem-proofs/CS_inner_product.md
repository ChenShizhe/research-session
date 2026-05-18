---
kind: theorem-proof
node_id: CS_inner_product
statement-file: theorems/CS_inner_product.md
dependencies:
  - inner product
  - norm
lean_status: verified
lean_file: lean/SyntheticExample/Translated/Theorems/CS_inner_product.lean
lean_attempted_at: 2026-05-18T08:30:00Z
lean_attempt_count: 2
lean_diagnostics_class: null
---

# Proof of Cauchy-Schwarz inequality

Direct from `Mathlib.Analysis.InnerProductSpace.Basic`. The lemma `abs_inner_le_norm` states exactly $|\langle u, v \rangle| \le \|u\| \cdot \|v\|$ for any inner product space, so the proof reduces to one term application.
