---
type: regex
target:
  source: file
  path: Invoices/InvoiceService.cs
match: count:0
---
(?<![.:\w])(?:str|int|arr|lst|obj|bool|dbl|flt)[A-Z][a-z]\w*(?!\w|\s*\()
