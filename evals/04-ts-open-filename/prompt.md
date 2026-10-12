---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, none]
---
In my TypeScript project I need two small functions: one formats an integer number of cents as a dollar string like `$1,234.50`, the other formats a `Date` as `YYYY-MM-DD`. Put them in a new file under `src/`.
