---
type: regex
target:
  source: file
  path: src/main/kotlin/com/acme/pricing/DiscountService.kt
match: count:0
---
:\s*Any\??(?=[\s,)=>]|$)|<\s*Any\??\s*>|,\s*Any\??\s*>
