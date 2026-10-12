---
type: regex
target:
  source: file
  path: app/bookings/router.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
