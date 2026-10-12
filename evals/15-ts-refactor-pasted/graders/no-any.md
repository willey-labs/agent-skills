---
type: regex
target:
  source: file
  path: src/invoiceExport.ts
match: count:0
---
[:<,|(]\s*any\b|\bas\s+any\b|\bany\s*\[\]
