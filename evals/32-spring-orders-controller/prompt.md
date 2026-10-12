---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [java, write, spring-boot]
---
Add orders to our Spring Boot 3 app (Java 21). Write `src/main/java/com/acme/orders/OrderController.java` and `src/main/java/com/acme/orders/OrderService.java`:

- `POST /orders` takes a customer ID and lines (product ID and quantity). Before anything is saved, check every line against the stock from the existing `InventoryRepository` (`int availableQuantity(String productId)`). If any line asks for more than is available, reject the whole order with `409` and list the product IDs that are short. Otherwise create the order with `Order.place(String customerId, List<OrderLine> lines)`, save it with the existing `OrderRepository` (a `JpaRepository<Order, UUID>`), and respond `201` with it.
- `GET /orders/{id}` returns the order, or `404` when there is none with that ID.

The `Order` entity (`getId()`, `getCustomerId()`, `getLines()`) and `OrderLine` (`new OrderLine(productId, quantity)`, `getProductId()`, `getQuantity()`) already exist in the same package.
