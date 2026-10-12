---
type: regex
target:
  source: file
  path: payments/gateway_client.py
match: count:0
---
(?:^|\n)[ \t]*#(?!!)[^\n]*\n[ \t]*#
