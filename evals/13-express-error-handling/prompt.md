---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, node-express]
---
Write a small Express 4 + TypeScript app in `src/app.ts`. Keep it all in that one file and export the app without calling `listen`; our tests drive it with supertest.

It has one route, `POST /transfers`, taking JSON `{ fromAccountId, toAccountId, amount }` and moving `amount` between two accounts kept in an in-memory `Map` (seed `acc-1` with 100 and `acc-2` with 50). On success it responds 200 with both accounts' new balances.

The transfer can fail three ways:

- the body is invalid (an id that isn't a non-empty string, or an amount that isn't a positive number) → 400
- either account doesn't exist → 404
- the source account's balance is less than the amount → 409

Define a domain error type for these failures, and handle every error in one central error-handling middleware that maps it to its status code and a `{ "error": { "code", "message" } }` body. Any other error becomes a 500 with a generic message.
