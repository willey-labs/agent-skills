---
type: regex
target:
  source: file
  path: src/main/kotlin/com/acme/pricing/DiscountService.kt
match: count:0
---
(?<![.:\w])(?:str|int|arr|lst|obj|bool|dbl|flt)[A-Z][a-z]\w*(?!\w|\s*\()
