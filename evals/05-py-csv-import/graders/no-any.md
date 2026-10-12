---
type: regex
target:
  source: file
  path: import_customers.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
