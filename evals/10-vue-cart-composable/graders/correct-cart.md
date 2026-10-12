---
type: llm
focus:
  source: file
  path: src/composables/useCart.ts
---
The file is a Vue 3 composable that manages a shopping cart. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (setting the quantity of a product not in the cart, price rounding, currency formatting, persistence) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Adding a product not in the cart creates a line with quantity 1; adding a product already in the cart (same `id`) increases that line's quantity by 1 instead of adding a second line.
2. Removing a product deletes its line.
3. Setting a quantity of 0 or less removes the line; a positive quantity replaces the line's quantity.
4. The total is a `computed` that sums price × quantity over all lines, and the item count is a `computed` that sums the line quantities.
5. The cart state is reactive (`ref` or `reactive`) and is created once, at module scope or through `provide`/`inject`, so every caller of `useCart()` sees the same lines. State created inside `useCart` on each call fails this claim.
