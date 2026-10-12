---
type: regex
target:
  source: file
  path: inventory/reservation.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
