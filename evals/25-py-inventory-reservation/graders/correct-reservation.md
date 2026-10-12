---
type: llm
focus:
  source: file
  path: inventory/reservation.py
---
The file reserves an order's stock across warehouses, nearest first. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (a failing `release`, exceptions other than `StockTaken`, the same SKU on two lines, zero quantities, logging) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Warehouses are tried in the order `warehouses_by_distance(order.destination_postcode)` returns them.
2. For each line it reserves, from each warehouse in turn, the smaller of what that warehouse has available and what the line still needs, skips warehouses with nothing available, and stops once the line is covered, so it never reserves more than the line's quantity.
3. When a line can't be covered in full, every reservation already made for the order (earlier lines and the covered part of the current line) is released, and the caller learns which SKU was short, through an exception or a failure result.
4. When `reserve` raises `StockTaken`, the order is not left holding partial reservations: either the code moves on to the next warehouse, or it releases everything reserved so far before the failure reaches the caller.
5. On success the result lists each reservation's warehouse, SKU, quantity and reservation id.
6. The success result is a declared type (dataclass, NamedTuple, TypedDict or class), not a bare dict or tuple.
