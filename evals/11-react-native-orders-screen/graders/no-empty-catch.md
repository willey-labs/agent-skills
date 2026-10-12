---
type: regex
target:
  source: file
  path: src/features/orders/OrdersScreen.tsx
match: count:0
---
catch\s*(?:\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(?:\{\s*\}|undefined|null)\s*\)
