---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, none]
---
Write `fetchUserProfile.ts` that exports a function to load a user profile from `GET /api/users/:id` using the global `fetch`. Retry up to 3 times when the server answers with a 5xx status; any other non-OK status fails immediately. The response JSON has `id`, `name`, `email` and `created_at` (an ISO string); return it as a profile whose `createdAt` is a `Date`.
