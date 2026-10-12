---
type: regex
target:
  source: file
  path: app/Http/Controllers/PostController.php
match: count:0
---
\b(?:var_dump|dd|print_r)\s*\(
