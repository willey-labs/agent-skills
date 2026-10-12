---
type: regex
target:
  source: file
  path: Billing/LateFeeCalculator.cs
match: count:0
---
//\s*(?:calculate the late fee for an invoice|days late after the grace period|VIPs pay half)
