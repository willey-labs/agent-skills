---
type: regex
target:
  source: file
  path: orders/services.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
