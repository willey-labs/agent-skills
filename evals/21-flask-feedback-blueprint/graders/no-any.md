---
type: regex
target:
  source: file
  path: app/feedback/routes.py
match: count:0
---
import[^\n]*\bAny\b|(?:[:\[,]|->)\s*Any\b
