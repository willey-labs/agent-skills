---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, nextjs]
---
Add a `/catalog` page to our Next.js App Router app (TypeScript and Tailwind; routes live in `app/`). It shows the products in a responsive grid, each with its image, name, category and price, and a search box above the grid that filters it as you type, matching name or category, case-insensitive. Show "No products match" when the search finds nothing.

There's no backend yet, so hard-code about eight products for now. They'll come from an API later.
