---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [kotlin, write, spring-boot]
---
In our Spring Boot pricing module (Kotlin), write `src/main/kotlin/com/acme/pricing/DiscountService.kt`, holding the discount rule types and a service that applies a list of rules to a cart. A cart has one line per SKU (SKU, unit price, quantity); money is `BigDecimal`.

Rule kinds:
- a percentage off the whole cart (`10` means 10%);
- a fixed amount off the cart;
- buy X get Y free on a SKU: for every X + Y units of that SKU, Y of them are free (buy 2 get 1 on 7 units makes 2 free).

All the rules in the list apply together: each one's discount is worked out on the original cart, and the discounts add up. The total discount can't exceed 30% of the cart subtotal. Return the subtotal, the total discount and the price to pay.
