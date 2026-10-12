---
type: llm
focus:
  source: file
  path: orders/models.py
---
The file holds the Django models of a shop's `orders` app, changed to support cancelling an order. Before the change it had `Product` (`name`, `stock`), `Order` (`Status` choices pending, paid, shipped and delivered; fields `customer`, `status`, `created_at`) and `OrderItem` (`order`, `product`, `quantity`). Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (the `on_delete` choice, related names, indexes, cancellation reasons) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. `Order.Status` gains a cancelled value and keeps pending, paid, shipped and delivered.
2. `Order` gains a nullable foreign key to the user model (`settings.AUTH_USER_MODEL` or `get_user_model()`) recording who cancelled it, and a nullable date-time field recording when.
3. Every field `Product`, `Order` and `OrderItem` had before is still there with its original type.
4. If the file defines which statuses can be cancelled (a constant, property or method), it allows exactly pending and paid.
