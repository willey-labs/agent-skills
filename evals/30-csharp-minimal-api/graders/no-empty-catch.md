---
type: regex
target:
  source: file
  path: Invoices/InvoiceService.cs
match: count:0
---
catch\s*(?:\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(?:\{\s*\}|undefined|null)\s*\)
