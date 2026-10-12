---
type: regex
target:
  source: file
  path: app/Http/Controllers/PostController.php
match: count:0
---
\$(?:str|int|arr|obj|bool)[A-Z]
