---
type: llm
focus:
  source: file
  path: import_customers.py
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `res`, `tmp`, `val`, `dt`, `cust`, and no single-letter names except a loop or comprehension variable used within one or two lines.
2. No function body is longer than 25 lines.
3. Valid customers and rejections are typed records (dataclass, NamedTuple or TypedDict), not bare tuples or untyped dicts.
4. No `#` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore docstrings and comment length; another check covers those.
