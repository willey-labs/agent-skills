---
type: regex
target:
  source: file
  path: src/invoiceExport.ts
match: count:0
---
//\s*(?:build the header row|loop over the invoices|skip void invoices unless asked|format the date as)
