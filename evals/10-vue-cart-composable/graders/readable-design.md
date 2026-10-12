---
type: llm
focus:
  source: file
  path: src/composables/useCart.ts
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `tmp`, `val`, `obj`, `qty`, `idx`, `prod`, and no single-letter names except a loop or callback parameter used within one or two lines.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no store class, event bus, generic state-container factory, or persistence layer for an in-memory cart.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments and comment length; another check covers those.
