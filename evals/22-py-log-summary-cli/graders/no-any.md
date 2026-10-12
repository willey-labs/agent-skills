---
type: regex
target:
  source: file
  path: log_summary.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
