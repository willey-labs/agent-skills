---
type: llm
focus:
  source: file
  path: internal/report/report.go
---
The user pasted `BuildReport(strTitle string, arrRows []map[string]interface{}, intLimit int, bTotals bool, strCurrency string, strOutPath string) string` and asked for a minimum-amount filter. Code carried over from the paste unchanged is not judged. If any parameter of `BuildReport` was renamed, added, removed, reordered or retyped, the parameter list counts as rewritten and is judged like new code; adding an `error` result alone does not. Grade only code the agent added or rewrote: the filter, any new types, functions, struct fields or variables, and a rewritten parameter list. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. No new name uses a type prefix such as `str`, `arr`, `int`, `flt`, `b` followed by a capital letter.
2. No new function, and no rewritten `BuildReport` parameter list, takes 5 or more parameters.
3. No new variable, struct field or helper introduces `interface{}` or `any`, apart from carrying the row maps the caller already passes in.
4. New names say what they hold or do: no abbreviations such as `min`, `amt`, `tmp`, `res`, `val`, `opts` used beyond one or two lines. Loop indexes, `err` and `ok` pass.
5. Nothing is more elaborate than a minimum filter needs: no filter interface, Strategy or registry, and no functional options (`WithX(...)` funcs). A plain struct grouping the inputs and a typed row struct are fine.
6. No `//` comment the agent added restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments. Apart from doc comments directly above the declaration they document, no comment runs past one line.
