---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [csharp, write, csharp]
---
Add invoice creation to our ASP.NET Core minimal API (.NET 8): `POST /invoices`. Map the endpoint in `Program.cs`, and put the validation and tax rules in `Invoices/InvoiceService.cs` behind one call that takes the request and gives back either the invoice or every validation problem.

The request has a `customerId` and `lines`, each with `description`, `quantity`, `unitPrice` (decimal) and `taxCategory`. Tax rates: `standard` 20%, `reduced` 5%, `zero` 0%. Tax is worked out per line on quantity × unit price and rounded to 2 decimals; the invoice shows the subtotal, the tax total and the grand total, plus a newly generated ID.

If `customerId` is empty, there are no lines, a quantity is below 1, a unit price is negative, or a tax category isn't one of the three, respond 400 with a validation problem listing every failing field. Otherwise respond 201 with the invoice. Nothing needs to be saved yet.
