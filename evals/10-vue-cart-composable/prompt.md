---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, vue-nuxt]
---
In our Vue 3 app (Vite, TypeScript, `<script setup>`, no Pinia), write a composable `src/composables/useCart.ts` and a component `src/components/CartSummary.vue` that uses it.

`useCart()` manages the shopping cart. A product has `id`, `name` and `price`. It needs to:

- add a product (adding one that's already in the cart bumps its quantity by 1)
- remove a product
- set a product's quantity (0 or less removes it)
- expose the cart lines, a computed total (price × quantity, summed) and a computed item count (the quantities added up)

Every component that calls `useCart()` should see the same cart.

`CartSummary.vue` lists the lines with the product name, a −/+ quantity control, the line total and a remove button, then the cart total. When the cart is empty it says "Your cart is empty".
