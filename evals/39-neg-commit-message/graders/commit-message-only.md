---
type: llm
focus: last_message
---
The user pasted a diff and asked for a commit message and nothing else. The diff makes `send_invoice` also send the invoice to the customer's `billing_email` when one is set and differs from their main email, and adds a test for that. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The reply is the commit message alone: no preamble such as "Here's a commit message", and no explanation, notes or alternatives after it. Wrapping the message in one code block is fine.
2. The subject line is at most 72 characters.
3. The message says invoices also go to the customer's billing email.
4. The message claims nothing the diff does not show: no change to retries, configuration, migrations or email templates.
