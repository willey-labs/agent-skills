---
type: llm
focus:
  source: file
  path: src/app.ts
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `acct`, `amt`, `bal`, `tmp`, `val`, and no single-letter names except a loop or callback parameter used within one or two lines. Express's conventional `req`, `res`, `next` and `err` parameters are fine.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no dependency-injection container, repository or service class hierarchy, or error-code registry for one route and three failures. An error subclass per failure, a small validation function, and an async wrapper are fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments and comment length; another check covers those.
