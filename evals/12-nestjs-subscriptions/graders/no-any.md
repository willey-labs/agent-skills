---
type: regex
target:
  source: file
  path: src/subscriptions/subscriptions.service.ts
match: count:0
---
[:<,|(]\s*any\b|\bas\s+any\b|\bany\s*\[\]
