---
type: regex
target:
  source: file
  path: pricing.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
