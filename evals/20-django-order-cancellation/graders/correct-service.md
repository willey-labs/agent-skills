---
type: llm
focus:
  source: file
  path: orders/services.py
---
The file cancels orders in a Django shop. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (permissions, notifications, refunds, cancellation reasons) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

Part of the work may be delegated to a method or constant on the `Order` model, which this file does not show. Accept a call such as `order.mark_cancelled(user)` or a check against `Order.CANCELLABLE_STATUSES` as doing the step a claim describes when its name says so.

1. A function cancels an order given the order (or its id) and the user cancelling it.
2. It raises an exception, without changing anything, when the order's status is not pending or paid.
3. It adds each order item's quantity back to that item's product stock.
4. It sets the order's status to cancelled, stores the cancelling user and the time of cancellation, and saves the order.
5. The status change and the restocking happen inside one `transaction.atomic()` block.
6. Two concurrent cancellations of the same order cannot both restock: either the order row is locked with `select_for_update()` and its status is checked after the lock is taken, or the status is changed with a conditional update (for example `Order.objects.filter(pk=..., status__in=[...]).update(...)`) whose row count decides whether to restock.
