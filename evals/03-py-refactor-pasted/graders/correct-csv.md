---
type: llm
focus:
  source: file
  path: report_builder.py
---
The file builds a report as plain text or CSV from a list of rows that each have a `name` and an `amount`. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (rows missing a field, unknown format values) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Plain-text output keeps the original shape: the title, then one `name: amount` line per row, then a `TOTAL: <sum>` line when totals are requested.
2. CSV output has a header row and one row per report row, with name and amount in separate columns.
3. CSV output quotes or escapes a name that contains a comma; using the `csv` module counts.
4. Both formats include only the first `limit` rows, and the total sums only those rows.
5. The caller picks the format through a parameter or a field, and plain text stays available.
