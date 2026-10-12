---
type: regex
target:
  source: file
  path: app/Http/Controllers/PostController.php
match: count:0
---
catch\s*(?:\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(?:\{\s*\}|undefined|null)\s*\)
