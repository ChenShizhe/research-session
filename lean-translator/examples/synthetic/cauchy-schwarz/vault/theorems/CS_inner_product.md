---
kind: theorem
node_id: CS_inner_product
title: Cauchy-Schwarz inequality for inner product spaces
dependencies:
  - inner product
  - inner product space
  - norm
  - Cauchy-Schwarz
lean_status: verified
lean_file: lean/SyntheticExample/Translated/Theorems/CS_inner_product.lean
lean_attempted_at: 2026-05-18T08:30:00Z
lean_attempt_count: 2
lean_diagnostics_class: null
---

# Cauchy-Schwarz inequality

**Statement.** Let $E$ be an inner product space over $\mathbb{K} \in \{\mathbb{R}, \mathbb{C}\}$, and let $u, v \in E$. Then
$$
|\langle u, v \rangle| \le \|u\| \cdot \|v\|.
$$

The inequality specializes to every finite-dimensional inner product space (Euclidean spaces, function spaces with a fixed inner product, etc.) since these are instances of the general inner-product-space structure.
