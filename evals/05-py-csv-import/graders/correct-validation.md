---
type: llm
focus:
  source: file
  path: import_customers.py
---
The file imports customers from a CSV and separates valid rows from rejected ones. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (missing columns, encodings, extra validation) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The CSV is read using its header row for column names (for example `csv.DictReader`), inside a `with` block or equivalent that closes the file.
2. A row whose email has no `@` is rejected, and its reason mentions the email.
3. A row whose `signup_date` is not a real calendar date is rejected (`2024-02-30` fails), and its reason mentions the date. Parsing with `date.fromisoformat` or `datetime.strptime(value, "%Y-%m-%d")` satisfies this.
4. Every input row ends up in exactly one of the two results: valid customers or rejected rows.
5. Each rejected entry keeps the original row data or its line number together with the reason.
