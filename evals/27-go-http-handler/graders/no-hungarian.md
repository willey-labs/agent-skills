---
type: regex
target:
  source: file
  path: internal/signup/handler.go
match: count:0
---
(?<![.:\w])(?:str|int|arr|lst|obj|bool|dbl|flt)[A-Z][a-z]\w*(?!\w|\s*\()
