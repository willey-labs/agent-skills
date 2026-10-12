---
type: llm
focus:
  source: file
  path: Billing/LateFeeCalculator.cs
---
The user pasted `LateFeeCalculator.Calculate(string strInvoiceId, decimal decAmount, DateTime dtDue, DateTime dtPaid, bool bIsVip, decimal decMinFee)`, which returns `dynamic`, and asked for a percentage cap. Code carried over from the paste unchanged is not judged. If any parameter of `Calculate` was renamed, added, removed, reordered or retyped, or its return type changed, the signature counts as rewritten and is judged like new code. Grade only code the agent added or rewrote: the cap logic, any new types, methods, properties, fields or variables, and a rewritten signature. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. No new name uses a type prefix such as `str`, `dec`, `int`, `dt`, `b`, `obj` followed by a capital letter, or an `m_` field prefix.
2. No new method, and no rewritten `Calculate` signature, takes 5 or more parameters. The positional components of a record that groups the caller's inputs are fields, not parameters, for this claim.
3. No new or rewritten declaration uses `dynamic`, or `object` standing in for a value whose shape is known.
4. New names say what they hold or do: no abbreviations such as `pct`, `amt`, `tmp`, `res`, `val`, `calc` used beyond one or two lines.
5. Nothing is more elaborate than a cap needs: no fee-rule interface or chain of rule classes, Strategy/Factory pattern, or builder. A record grouping the caller's inputs, a result record and a private helper method are fine.
6. No `//` comment the agent added restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments. Apart from doc comments directly above the declaration they document, no comment runs past one line.
