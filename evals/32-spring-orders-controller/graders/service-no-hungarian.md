---
type: regex
target:
  source: file
  path: src/main/java/com/acme/orders/OrderService.java
match: count:0
---
(?<![.:\w])(?:str|int|arr|lst|obj|bool|dbl|flt)[A-Z][a-z]\w*(?!\w|\s*\()
