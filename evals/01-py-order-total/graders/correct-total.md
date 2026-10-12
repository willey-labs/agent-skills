---
type: llm
focus:
  source: file
  path: pricing.py
---
The file computes an order total. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (invalid input, rounding, unknown values) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The subtotal is the sum of unit price × quantity over all line items.
2. The discount code `SAVE10` takes 10% off the subtotal, and no code takes nothing off. An unrecognized code may either take nothing off or raise an error; both pass.
3. Tax is the tax rate applied to the discounted subtotal; shipping is not taxed.
4. Shipping is 5 for region `US`, 8 for `EU`, 15 for any other region, and 0 when the customer is a member.
5. The total is discounted subtotal + tax + shipping.
