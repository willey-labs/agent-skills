---
type: llm
focus:
  source: file
  path: internal/signup/handler.go
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `tmp`, `res`, `val`, `usr`, `pw`, `dn`, and no single-letter names except a method receiver, a loop variable used within one or two lines, and `w` and `r` for the response writer and request. The Go idioms `ctx`, `err`, `ok`, `req` and `id` pass.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no validation framework or rule registry, no generic error-to-status table or middleware chain for three store outcomes, no Strategy/Factory pattern. A request struct, a validation function and a sentinel error are fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments. Apart from doc comments directly above the declaration they document, no comment runs past one line.
