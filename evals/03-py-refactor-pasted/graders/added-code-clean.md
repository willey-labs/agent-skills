---
type: llm
focus:
  source: file
  path: report_builder.py
---
The user pasted a function `build_report(strTitle, lstRows, intLimit, bIncludeTotals, strFormat)` and asked for a CSV option. Keeping that public signature exactly unchanged is acceptable; do not judge it. If any parameter of `build_report` was renamed, added, removed or reordered, the signature counts as rewritten and is judged like new code. Grade only code the agent added or rewrote: the CSV path, any new helper functions or variables, and a rewritten signature. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. No new name uses a type prefix such as `str`, `lst`, `int`, `b`, `arr` followed by a capital letter.
2. No new function, and no rewritten `build_report` signature, takes 5 or more parameters.
3. New names say what they hold or do: no abbreviations such as `buf`, `r`, `tmp`, `res` used beyond one or two lines.
4. The plain-text and CSV paths share the row selection and totals logic instead of duplicating the loop.
5. Nothing is more elaborate than a choice between two formats needs: no registry or dispatch table of renderers, Strategy/Factory pattern, or extra class whose only job is carrying data between two private functions. A dataclass that groups the caller's parameters, an Enum or string for the format, and a custom error class are fine.
