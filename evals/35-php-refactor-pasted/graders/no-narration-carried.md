---
type: regex
target:
  source: file
  path: src/Shipping/RateCalculator.php
match: count:0
---
//\s*(?:calculate the shipping price for a parcel|start from the zone price|every started kg over 2 kg costs 1\.25)
