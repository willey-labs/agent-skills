---
type: llm
focus:
  source: file
  path: src/main/java/com/acme/orders/OrderService.java
---
The file is a Spring service that places and looks up orders. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (the same product on two lines, quantities of zero or less, reserving or decrementing stock, transactions, how the controller maps exceptions to status codes) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Placing an order reads the available quantity of every line's product through the injected `InventoryRepository` before anything is saved.
2. A line is short when its quantity is greater than the available quantity; a line asking for exactly the available quantity is accepted.
3. When any line is short, nothing is saved and the rejection carries every short product ID, not only the first (for example an exception holding the list).
4. When no line is short, the order is created with `Order.place` from the customer ID and the requested lines, saved through `OrderRepository`, and the saved order (or a response built from it) is returned.
5. Looking up an order returns it when it exists; when it doesn't, the service throws a not-found exception or returns an empty `Optional`, never `null`.
6. Both repositories reach the service through its constructor (or Spring field injection), never `new` or a static lookup.
