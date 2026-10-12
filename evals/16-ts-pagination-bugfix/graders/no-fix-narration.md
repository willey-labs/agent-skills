---
type: llm
focus:
  source: file
  path: src/paginate.ts
---
The user pasted a pagination function with two bugs and asked for a fix. Grade only the comments in this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. No comment describes the bug or the change being made, such as "fixed", "was `Math.floor`", "previously", "off-by-one", or "use ceil instead of floor".
2. No `//` comment restates what the next line does or addresses a reader.

Ignore doc comments and comment length; another check covers those. A file with no comments passes.
