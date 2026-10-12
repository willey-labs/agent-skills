---
type: regex
target:
  source: file
  path: src/app.ts
match: count:0
---
[:<,|(]\s*any\b|\bas\s+any\b|\bany\s*\[\]
