---
type: llm
focus:
  source: file
  path: log_summary.py
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. Printing to stdout is this script's output, not leftover debugging. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `cnt`, `ln`, `lat`, `tmp`, `res`, `val`, and no single-letter names except a loop, comprehension or `except ... as` variable, or a regex match, used within one or two lines.
2. No function body is longer than 25 lines.
3. Reading and parsing lines, aggregating the counts, and printing the report are not all done in one function.
4. Nothing is more elaborate than the task needs: no class hierarchy, abstract base class, plugin or formatter registry, or configuration object for one log format and one report. A dataclass for a parsed line or for the summary is fine.
5. No `#` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore docstrings and comment length; another check covers those.
