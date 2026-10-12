---
type: regex
target:
  source: file
  path: src/invoiceExport.ts
match: count:0
---
catch\s*(?:\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(?:\{\s*\}|undefined|null)\s*\)
