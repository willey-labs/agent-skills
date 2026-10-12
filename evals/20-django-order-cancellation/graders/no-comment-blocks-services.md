---
type: regex
target:
  source: file
  path: orders/services.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
