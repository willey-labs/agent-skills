---
type: regex
target:
  source: file
  path: log_summary.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
