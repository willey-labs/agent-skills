---
type: llm
focus:
  source: file
  path: internal/fetch/fetch.go
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `tmp`, `res`, `val`, `cnt`, `lim`, and no single-letter names except a method receiver or a loop variable used within one or two lines. The Go idioms `ctx`, `err`, `ok`, `req`, `resp`, `wg`, `mu` and `sem` pass.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than the task needs: no reusable generic worker pool or job queue meant for any kind of job, and no retries, backoff or functional options the task never asked for. A result struct with a semaphore channel, a fixed set of workers reading a channel, or `errgroup` are all fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments. Apart from doc comments directly above the declaration they document, no comment runs past one line.
