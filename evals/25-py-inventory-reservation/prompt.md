---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, none]
---
Write `inventory/reservation.py`: reserve stock for an order across our warehouses. For each order line, take stock from the warehouse nearest the order's destination that has any, then the next nearest, and so on until the line is covered. If any line can't be covered in full, release everything already reserved for the order and report which SKU was short. On success, return a typed result saying how much of each SKU was reserved in which warehouse, with the reservation ids.

These already exist in `inventory.stock`:

```python
@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int


@dataclass(frozen=True)
class Order:
    id: str
    destination_postcode: str
    lines: list[OrderLine]


class StockTaken(Exception):
    pass


class StockService(Protocol):
    def warehouses_by_distance(self, postcode: str) -> list[str]: ...

    def available(self, warehouse_id: str, sku: str) -> int: ...

    def reserve(self, warehouse_id: str, sku: str, quantity: int) -> str: ...

    def release(self, reservation_id: str) -> None: ...
```

`warehouses_by_distance` returns warehouse ids, nearest first. `reserve` returns a reservation id, and raises `StockTaken` if another order took the stock between `available` and `reserve`.
