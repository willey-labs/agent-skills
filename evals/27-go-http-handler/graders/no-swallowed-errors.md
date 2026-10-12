---
type: regex
target:
  source: file
  path: internal/signup/handler.go
match: count:0
---
_\s*=\s*err\b|if\s+err\s*!=\s*nil\s*\{\s*\}
