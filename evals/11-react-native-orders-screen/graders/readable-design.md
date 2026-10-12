---
type: llm
focus:
  source: file
  path: src/features/orders/OrdersScreen.tsx
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `res`, `tmp`, `val`, `ord`, `amt`, and no single-letter names except a loop or callback parameter used within one or two lines.
2. No function or component body is longer than 25 lines, not counting the JSX markup it returns.
3. Nothing is more elaborate than the task needs: no data-fetching library, global store, reducer with action types, or generic async-state hook with options the task never asked for. A small hook for this screen's load and refresh state is fine.
4. No `//` or `{/* */}` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments and comment length; another check covers those.
