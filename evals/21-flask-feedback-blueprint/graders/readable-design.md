---
type: llm
focus:
  source: file
  path: app/feedback/routes.py
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `fb`, `req`, `res`, `tmp`, `val`, `pp`, and no single-letter names except a loop, comprehension or `except ... as` variable used within one or two lines.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no class-based views, hand-built validation framework (generic field or rule classes), schema base class, or registry for two endpoints and three fields. A small dataclass or schema for the validated input, a validation function, and a custom error class with a blueprint error handler are fine.
4. No `#` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore docstrings and comment length; another check covers those.
