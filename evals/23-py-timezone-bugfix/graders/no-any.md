---
type: regex
target:
  source: file
  path: store_hours.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
