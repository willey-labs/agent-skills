---
type: llm
focus:
  source: file
  path: src/retry/withRetry.ts
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `res`, `tmp`, `val`, `cfg`, `opts`, `fn` used beyond one or two lines, and no single-letter names except a loop or callback parameter used within one or two lines. A generic type parameter `T` is fine.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no class hierarchy, Strategy/Factory pattern for backoff policies, or options the task never asked for (jitter, abort signals, logging hooks, maximum delay). One options object holding the three settings is fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments and comment length; another check covers those.
