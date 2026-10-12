---
type: regex
target:
  source: file
  path: src/main/java/com/acme/orders/OrderService.java
match: count:0
---
import\s+[\w.]+\.\*
