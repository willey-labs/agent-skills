---
type: regex
target:
  source: file
  path: app/bookings/schemas.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
