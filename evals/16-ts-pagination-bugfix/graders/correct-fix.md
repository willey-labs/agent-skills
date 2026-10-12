---
type: llm
focus:
  source: file
  path: src/paginate.ts
---
The file paginates an array. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (page numbers below 1 or past the end, a page size of 0 or less, an empty list) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. `totalPages` is the item count divided by the page size, rounded up: 25 items with page size 10 give 3, and 30 items give 3.
2. Each page returns the items from index `(page − 1) × pageSize` up to but not including `page × pageSize`, cut off at the end of the list: page 3 of 25 items with page size 10 returns the 5 items at indices 20–24, including the last item, and page 1 returns indices 0–9.
3. `hasNextPage` is true on pages 1 and 2 and false on page 3 for 25 items with page size 10.
4. Callers need no changes: `paginate` takes the same arguments in the same order, and the returned object has the same fields as the `Page<T>` interface in the original code.
