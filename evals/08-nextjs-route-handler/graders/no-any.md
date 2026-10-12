---
type: regex
target:
  source: file
  path: app/api/orders/route.ts
match: count:0
---
[:<,|(]\s*any\b|\bas\s+any\b|\bany\s*\[\]
