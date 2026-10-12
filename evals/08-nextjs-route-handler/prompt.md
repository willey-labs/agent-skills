---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, nextjs]
---
In our Next.js App Router project (TypeScript), add `app/api/orders/route.ts` with a `POST` handler that quotes an order.

The request body is JSON like `{ "items": [{ "sku": "ABC-1", "price": 12.5, "quantity": 2 }], "coupon": "WELCOME10" }`, where `coupon` is optional. Validate it:

- `items` must be a non-empty array
- each item's `sku` is a non-empty string, `price` is a number of 0 or more, and `quantity` is a positive integer
- `coupon`, when present, must be `WELCOME10`, the only coupon we have

If anything is invalid, respond 400 with `{ "errors": { "<field>": "<message>" } }` listing every invalid field, using paths like `items.1.quantity` for item fields. A body that isn't valid JSON is also a 400. Otherwise respond 200 with `{ "subtotal", "discount", "total" }`: subtotal is the sum of price × quantity, `WELCOME10` takes 10% off it, and total is subtotal minus discount.

We don't have zod or any other validation library, so plain TypeScript please. Keep it all in `route.ts` for now; we'll split it out once there are more order endpoints.
