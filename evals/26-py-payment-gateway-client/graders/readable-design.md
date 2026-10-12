---
type: llm
focus:
  source: file
  path: payments/gateway_client.py
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `resp`, `res`, `cfg`, `amt`, `tmp`, `val`, and no single-letter names except a loop, comprehension or `except ... as` variable used within one or two lines.
2. No function body is longer than 25 lines.
3. Turning a response status into one of the errors is written once and shared by charging and refunding, not repeated in each.
4. Nothing is more elaborate than the task needs: no abstract gateway base class, provider registry, plugin system or generic retry framework for one provider with two calls. An error hierarchy and small result dataclasses are fine.
5. No `#` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore docstrings and comment length; another check covers those.
