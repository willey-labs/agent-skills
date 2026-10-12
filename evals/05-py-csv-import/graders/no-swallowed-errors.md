---
type: regex
target:
  source: file
  path: import_customers.py
match: count:0
---
except\s*:|except[^\n]*:[ \t]*(?:#[^\n]*)?\n?\s*(?:pass|continue)\b
