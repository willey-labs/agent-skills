---
type: regex
target:
  source: file
  path: inventory/reservation.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
