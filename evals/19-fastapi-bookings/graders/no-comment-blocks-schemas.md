---
type: regex
target:
  source: file
  path: app/bookings/schemas.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
