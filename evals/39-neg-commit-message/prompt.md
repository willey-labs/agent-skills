---
max_turns: 10
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob, Grep]
model: opus
runs: 3
plugins: [../..]
tags: [negative]
---
Write a commit message for this diff. Just the message, nothing else.

```diff
diff --git a/src/billing/invoice_mailer.py b/src/billing/invoice_mailer.py
index 3f2a9c1..8b7e4d0 100644
--- a/src/billing/invoice_mailer.py
+++ b/src/billing/invoice_mailer.py
@@ -14,5 +14,7 @@ def send_invoice(invoice, smtp_client):
     message = build_invoice_message(invoice)
     recipients = [invoice.customer.email]
+    if invoice.customer.billing_email and invoice.customer.billing_email != invoice.customer.email:
+        recipients.append(invoice.customer.billing_email)
     smtp_client.send(message, to=recipients)
     invoice.sent_at = datetime.now(timezone.utc)
     invoice.save()
diff --git a/tests/billing/test_invoice_mailer.py b/tests/billing/test_invoice_mailer.py
index 71c04be..e2d9a13 100644
--- a/tests/billing/test_invoice_mailer.py
+++ b/tests/billing/test_invoice_mailer.py
@@ -31,2 +31,10 @@ def test_send_invoice_sets_sent_at(invoice, fake_smtp):
     send_invoice(invoice, fake_smtp)
     assert invoice.sent_at is not None
+
+
+def test_send_invoice_copies_billing_email(invoice, fake_smtp):
+    invoice.customer.billing_email = "accounts@example.com"
+
+    send_invoice(invoice, fake_smtp)
+
+    assert fake_smtp.sent[0].to == [invoice.customer.email, "accounts@example.com"]
```
