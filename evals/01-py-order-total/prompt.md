---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, none]
---
Write a Python function in `pricing.py` that calculates an order's total. It needs the line items (each has a unit price and a quantity), an optional discount code, the tax rate, the customer's shipping region, and whether the customer is a member.

Rules: discount code `SAVE10` takes 10% off the subtotal. Tax applies to the discounted subtotal, not to shipping. Shipping is 5 for region `US`, 8 for `EU`, 15 anywhere else. Members ship free.
