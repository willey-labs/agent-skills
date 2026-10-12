---
type: regex
target:
  source: file
  path: app/login/login-view-model.ts
match: count:0
---
[:<,|(]\s*any\b|\bas\s+any\b|\bany\s*\[\]
