---
type: regex
target:
  source: file
  path: src/components/CartSummary.vue
match: count:0
---
[:<,|(]\s*any\b|\bas\s+any\b|\bany\s*\[\]
