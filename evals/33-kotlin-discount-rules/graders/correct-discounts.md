---
type: llm
focus:
  source: file
  path: src/main/kotlin/com/acme/pricing/DiscountService.kt
---
The file applies stacked discount rules to a cart. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (rounding, negative or zero inputs, an X or Y of zero, the same rule twice) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The subtotal is the sum of unit price × quantity over the cart lines.
2. A percentage rule's discount is that percentage of the subtotal, where `10` means 10%.
3. A fixed-amount rule's discount is its amount.
4. A buy-X-get-Y rule frees (quantity of its SKU ÷ (X + Y), rounded down) × Y units, valued at that SKU's unit price, and gives nothing when the SKU is not in the cart.
5. Every rule's discount is computed from the original cart, not from a price another rule already reduced, and the discounts are summed.
6. The summed discount is capped at 30% of the subtotal, and the price to pay is the subtotal minus the capped discount.
7. The result gives the subtotal, the capped total discount and the price to pay.
