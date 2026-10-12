---
type: regex
target:
  source: file
  path: import_customers.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
