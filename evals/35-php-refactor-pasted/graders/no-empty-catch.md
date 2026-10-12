---
type: regex
target:
  source: file
  path: src/Shipping/RateCalculator.php
match: count:0
---
catch\s*(?:\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(?:\{\s*\}|undefined|null)\s*\)
