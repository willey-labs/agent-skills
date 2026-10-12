---
type: llm
focus:
  source: file
  path: Invoices/InvoiceService.cs
---
The file validates an invoice request and computes the invoice. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (rounding mode, message wording, the format of field keys, letter case of tax category names, where the ID is generated) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Validation flags each of: an empty `customerId` (treating whitespace as empty also passes), a missing or empty list of lines, a line quantity below 1, a negative unit price, and a tax category other than `standard`, `reduced` or `zero`.
2. Validation reports every failing field together, not only the first, keyed by field so a 400 validation problem can list them (for example a `Dictionary<string, string[]>`, a result object, or an exception carrying them).
3. The call that builds the invoice checks validity first: for an invalid request it gives back the validation problems (returned or thrown) and builds no invoice.
4. Each line's tax is quantity × unit price × its rate (standard 0.20, reduced 0.05, zero 0), rounded to 2 decimals per line.
5. The subtotal is the sum of quantity × unit price over all lines, the tax total is the sum of the rounded line taxes, and the grand total is subtotal + tax total.
