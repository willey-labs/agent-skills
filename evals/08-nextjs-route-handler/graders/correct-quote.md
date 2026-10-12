---
type: llm
focus:
  source: file
  path: app/api/orders/route.ts
---
The file is a Next.js route handler that validates an order body and returns a price quote. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (a JSON body that is not an object, rounding, the wording of error messages, the error key used for a body that is not JSON) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. It exports an async `POST` function that reads the request body as JSON, and a body that fails to parse as JSON gets a 400 response instead of an unhandled exception.
2. It responds 400 when `items` is missing, not an array, or empty; when an item's `sku` is not a non-empty string; when an item's `price` is not a number or is negative; when an item's `quantity` is not a positive integer; and when `coupon` is present but is not `WELCOME10`.
3. The 400 body is `{ errors: { ... } }` with one entry per invalid field, collecting every invalid field instead of stopping at the first; item errors are keyed by a path naming the item index and the field, such as `items.1.quantity`.
4. A valid body gets a 200 response whose `subtotal` is the sum of price × quantity over all items.
5. `discount` is 10% of the subtotal with coupon `WELCOME10` and 0 with no coupon, and `total` is subtotal minus discount.
