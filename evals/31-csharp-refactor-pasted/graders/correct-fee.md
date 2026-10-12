---
type: llm
focus:
  source: file
  path: Billing/LateFeeCalculator.cs
---
The file calculates an invoice's late fee. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (negative amounts, a cap of zero or below, rounding mode, time zones) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Days late is the number of whole days from the due date to the paid date minus 3 grace days; when that is 0 or less there is no fee and the days late reported is 0.
2. When the invoice is late, the fee starts at amount × 0.001 × days late, is halved for VIP customers, and is then raised to the minimum fee if it is below it.
3. The fee is then capped at amount × cap percentage ÷ 100, so the cap applies after the VIP halving and the minimum fee and wins when it is lower than the minimum fee.
4. The cap percentage comes from the caller (a method parameter, a property of a request object, or a constructor argument), not from a constant.
5. The result still gives the invoice ID, the days late and the fee rounded to 2 decimals.
