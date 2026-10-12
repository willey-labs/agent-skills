---
type: regex
target:
  source: file
  path: orders/models.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
