---
type: llm
focus:
  source: file
  path: src/invoiceExport.ts
---
The file exports invoices as CSV, with an optional date range. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (invoices with no lines, malformed dates or range strings, time zones, a `from` later than `to`) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. With no range given, the output is what the original produced: the header `number,customer,issued,amount`, then one row per exported invoice with its number, the customer name (quoted when it contains a comma), the issue date as `YYYY-MM-DD`, and the amount with two decimals followed by a space and the currency.
2. Void invoices are still skipped unless the caller asks to include them, and that check still applies when a range is given.
3. With a range, only invoices whose issue date is on or after `from` and on or before `to` are exported, both ends inclusive by calendar day: an invoice issued at any time on the `to` date is included. A missing `from` or `to` leaves that side open.
4. An invoice's amount is still the sum of quantity × unit price over its lines.
5. The caller can still export without passing any range.
