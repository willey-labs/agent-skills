---
type: llm
focus:
  source: file
  path: inventory/reservation.py
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `qty`, `wh`, `rid`, `tmp`, `res`, `val`, and no single-letter names except a loop, comprehension or `except ... as` variable used within one or two lines.
2. No function body is longer than 25 lines.
3. Releasing the reservations made so far is written once, not repeated at each failure point.
4. Nothing is more elaborate than the task needs: no abstract allocator or Strategy pattern for nearest-first, no saga or unit-of-work framework for one rollback, no class hierarchy. Dataclasses for the result and a custom error class are fine.
5. No `#` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore docstrings and comment length; another check covers those.
