---
type: llm
focus:
  source: file
  path: src/checkout/applyGiftCard.js
---
Grade the design of this file. Ignore whether the logic is correct, and ignore `console.log` calls, `debugger` statements, commented-out code and empty `.catch` handlers; other checks cover those. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `amt`, `tmp`, `res`, `val`, `elig`, and no single-letter names except a callback parameter used within one or two lines.
2. No function body is longer than 25 lines, not counting the lines this grader ignores.
3. Nothing is more elaborate than the feature needs: no rules engine, eligibility policy class, options object, Strategy/Factory pattern, or configurable list of excluded item types for a single `isGiftCard` check.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments and comment length.
