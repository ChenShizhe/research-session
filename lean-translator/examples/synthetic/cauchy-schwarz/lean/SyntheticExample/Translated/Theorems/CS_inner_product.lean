import Mathlib.Analysis.InnerProductSpace.Basic

/-!
# Cauchy-Schwarz inequality

Translation of vault node `theorems/CS_inner_product.md`. Direct application of
Mathlib's `norm_inner_le_norm` in `Mathlib.Analysis.InnerProductSpace.Basic`.
-/

namespace SyntheticExample.Translated.Theorems

variable {𝕜 : Type*} [RCLike 𝕜]
variable {E : Type*} [NormedAddCommGroup E] [InnerProductSpace 𝕜 E]

theorem CS_inner_product (u v : E) :
    ‖inner 𝕜 u v‖ ≤ ‖u‖ * ‖v‖ :=
  norm_inner_le_norm u v

end SyntheticExample.Translated.Theorems
