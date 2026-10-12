---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, none]
---
Write `import_customers.py` with a function that reads a customers CSV file (columns: `name`, `email`, `signup_date`) and returns the valid customers plus the rejected rows, each with the reason it was rejected. A row is invalid when the email has no `@` or `signup_date` isn't a real date in `YYYY-MM-DD` format.
