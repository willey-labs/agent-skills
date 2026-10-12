---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, fix, none]
---
Our pagination helper is off. With 25 items and a page size of 10, page 3 shows only 4 items, and `totalPages` comes back as 2, so the UI never offers page 3. Can you fix it and save it as `src/paginate.ts`?

```ts
export interface Page<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNextPage: boolean;
}

export function paginate<T>(items: T[], page: number, pageSize: number): Page<T> {
  const totalPages = Math.floor(items.length / pageSize);
  const start = (page - 1) * pageSize;
  const end = Math.min(start + pageSize, items.length - 1);

  return {
    items: items.slice(start, end),
    page,
    pageSize,
    totalItems: items.length,
    totalPages,
    hasNextPage: page < totalPages,
  };
}
```
