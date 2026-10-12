---
type: llm
focus:
  source: file
  path: src/invoiceExport.ts
---
The user pasted a function `exportInvoices(arrInvoices: any[], strCurrency: string, bIncludeVoid: boolean)` and asked for an optional `from`/`to` date range. Keeping that signature exactly unchanged is acceptable; do not judge it. If any parameter of `exportInvoices` was renamed, added, removed, reordered or retyped, the signature counts as rewritten and is judged like new code. Grade only code the agent added or rewrote: the range filter, any new helper functions, types or variables, and a rewritten signature. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. No new name uses a type prefix such as `str`, `arr`, `lst`, `obj`, `dbl`, `dt`, `b` followed by a capital letter.
2. No new function, and no rewritten `exportInvoices` signature, takes 5 or more parameters.
3. New names say what they hold or do: no abbreviations such as `inv`, `dt`, `tmp`, `res`, `val` used beyond one or two lines.
4. Nothing is more elaborate than an optional date range needs: no filter registry, Strategy/Factory pattern, or class whose only job is carrying data between two private functions. An options object or a `DateRange` type for the parameters, and an `Invoice` interface, are fine.
