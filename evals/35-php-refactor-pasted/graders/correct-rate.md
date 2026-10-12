---
type: llm
focus:
  source: file
  path: src/Shipping/RateCalculator.php
---
The file calculates a shipping price for a parcel. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (unknown zones, missing or non-numeric parcel fields, negative weights or sizes) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The base price is 4.50 for `domestic`, 9.00 for `eu` and 15.00 for `world`.
2. When the weight is over 2 kg, each started kilogram over 2 adds 1.25 (ceil(weight − 2) × 1.25).
3. A parcel with any of `length_cm`, `width_cm` or `height_cm` over 120 adds 8.00; a side of exactly 120 adds nothing.
4. The surcharge is added before the express multiplier, so express multiplies the zone price, the weight charge and the surcharge together by 1.5.
5. The `FREESHIP` coupon makes a domestic parcel's price 0, surcharge included, and changes nothing for other zones.
6. The result is rounded to 2 decimals.
