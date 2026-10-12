---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, none]
---
Write a command-line script `log_summary.py` that summarizes a web server access log, run as `python log_summary.py access.log`. Each line looks like this, with the response time in seconds as the last field:

```
203.0.113.7 - - [12/Mar/2025:10:15:32 +0000] "GET /api/orders?page=2 HTTP/1.1" 200 512 0.084
```

Print the number of requests per status class (2xx, 3xx, 4xx, 5xx), the 5 most requested paths without their query strings, and the 95th-percentile response time in milliseconds. The logs contain some garbage lines (truncated writes, other formats); count those and report how many were skipped instead of crashing, even when no line is valid. Use argparse.
