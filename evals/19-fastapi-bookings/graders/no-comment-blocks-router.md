---
type: regex
target:
  source: file
  path: app/bookings/router.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
