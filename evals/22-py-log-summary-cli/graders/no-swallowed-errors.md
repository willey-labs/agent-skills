---
type: regex
target:
  source: file
  path: log_summary.py
match: count:0
---
except\s*:|except[^\n]*:[ \t]*(?:#[^\n]*)?\n?[ \t]*(?:pass|\.\.\.)[ \t]*(?:\n|$)
