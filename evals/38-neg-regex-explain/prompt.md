---
max_turns: 10
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob, Grep]
model: opus
runs: 3
plugins: [../..]
tags: [negative]
---
What does this regex match? Two or three sentences.

```
^(?:\+?1[-. ]?)?\(?(\d{3})\)?[-. ]?(\d{3})[-. ]?(\d{4})$
```
