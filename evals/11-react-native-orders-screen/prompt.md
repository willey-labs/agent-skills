---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, react-native]
---
In our Expo app (TypeScript), write `src/features/orders/OrdersScreen.tsx`, the screen that lists the signed-in user's orders.

It receives a `fetchOrders: () => Promise<Order[]>` prop, where an order is `{ id: string; placedAt: string; total: number; status: 'pending' | 'shipped' | 'delivered' }` (`placedAt` is an ISO date string, `total` is in dollars). Keep everything for this screen in that one file for now, including the `Order` type.

- While the first load runs, show a spinner.
- If loading fails, show an error message with a Retry button.
- If there are no orders, show "No orders yet".
- Otherwise show a list: each row has the order date, its status and its total formatted like `$1,234.50`.
- Pulling down on the list reloads it; a failed reload shows the same error state.
