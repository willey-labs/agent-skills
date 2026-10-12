---
type: llm
focus:
  source: file
  path: Invoices/InvoiceService.cs
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `amt`, `qty`, `tmp`, `res`, `val`, `inv`, `cat`, and no single-letter names except a loop variable or lambda parameter used within one or two lines. A leading underscore on a private field is the C# convention and passes.
2. No method body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no tax-rule interface or class per rate, Strategy/Factory pattern, rule registry, or MediatR-style command/handler layering for three fixed rates and five checks. An interface for the service, records for the request and the invoice, and a dictionary or `switch` for the rates are fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments (`///`). Apart from doc comments directly above the declaration they document, no comment runs past one line.
