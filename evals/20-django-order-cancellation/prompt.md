---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, django]
---
Add order cancellation to our Django shop's `orders` app. This is `orders/models.py` today:

```python
from django.conf import settings
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=200)
    stock = models.PositiveIntegerField(default=0)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PAID = "paid"
        SHIPPED = "shipped"
        DELIVERED = "delivered"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
```

Make the model changes in `orders/models.py` and put the cancellation itself in `orders/services.py`. Only pending or paid orders can be cancelled. Cancelling puts each item's quantity back into its product's stock and records who cancelled the order and when. Staff sometimes double-click, so two cancellations of the same order arriving together must not restock it twice. No views needed, and I'll generate the migration myself.
