---
max_turns: 10
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob, Grep, Write]
model: opus
runs: 3
plugins: [../..]
tags: [negative]
---
Write a short `README.md` for a command-line tool called `csv2json` that converts a CSV file to JSON. Usage: `csv2json input.csv [-o output.json] [--pretty]`.
