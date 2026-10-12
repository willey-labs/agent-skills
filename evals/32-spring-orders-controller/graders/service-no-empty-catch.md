---
type: regex
target:
  source: file
  path: src/main/java/com/acme/orders/OrderService.java
match: count:0
---
catch\s*(?:\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(?:\{\s*\}|undefined|null)\s*\)
