---
type: llm
focus:
  source: file
  path: internal/report/report.go
---
The file builds a plain-text sales report from rows that each have a `name` and an `amount`. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (rows missing a field, a negative limit, file permissions, how a failed write is reported) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Rows are listed from the largest amount to the smallest.
2. A row whose amount is below the minimum is not listed, does not count toward the row limit, and is not added to the total.
3. At most `limit` rows are listed, and the `TOTAL` line, present only when totals are requested, sums exactly the listed rows.
4. The report starts with the title line, and each listed line and the `TOTAL` line show the name (or `TOTAL`), the amount with two decimals, and the currency.
5. The report text is returned to the caller (an added `error` result is fine), and the file still offers writing it to the output path with the directory created first, either inside the report function or in a separate function.
6. The caller supplies the minimum, as a parameter or as a field of a struct the caller fills in.
