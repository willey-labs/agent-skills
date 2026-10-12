---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, none]
---
Write a framework-free TypeScript module `src/retry/withRetry.ts` that exports `withRetry`, which runs an async operation and retries it with exponential backoff.

The caller sets the maximum number of attempts (counting the first one), a base delay in milliseconds, and a predicate that decides whether an error is worth retrying. The wait before the n-th retry is `baseDelay × 2^(n−1)`, so with a base of 100 ms the waits are 100, 200, 400 and so on. An error the predicate rejects is thrown straight away; when the attempts run out, throw the last error. On success, return the operation's result. One file, no dependencies.
