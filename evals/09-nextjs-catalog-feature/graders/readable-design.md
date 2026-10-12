---
type: llm
focus: trace
---
The trace shows an agent asked to add a `/catalog` page with a product grid and a search filter to a Next.js App Router project. Find the Write and Edit tool calls that created the catalog's files and grade only the code in them. Ignore any reference documents or skill text the agent read, and ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `tmp`, `val`, `obj`, `prod`, `cat`, and no single-letter names except a loop or callback parameter used within one or two lines.
2. No function or component body is longer than 25 lines, not counting the JSX markup it returns.
3. Nothing is more elaborate than the task needs: no global state library, context provider, reducer, or generic data-fetching layer for one search box over a hard-coded list. Splitting the page into a few small components, and a plain function that returns the product list, are fine.
4. No `//` or `{/* */}` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments and comment length.
