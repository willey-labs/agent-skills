---
type: regex
target:
  source: file
  path: app/feedback/routes.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
