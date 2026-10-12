---
type: regex
target:
  source: file
  path: report_builder.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
