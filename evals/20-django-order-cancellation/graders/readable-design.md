---
type: llm
focus:
  source: file
  path: orders/services.py
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `qty`, `obj`, `tmp`, `res`, `val`, and no single-letter names except a loop, comprehension or `except ... as` variable used within one or two lines.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no state-machine library, command or service class hierarchy, abstract base class, or Strategy/Factory pattern for a single cancel transition. A custom error class is fine.
4. No `#` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore docstrings and comment length; another check covers those.
