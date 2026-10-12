---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
model: opus
runs: 3
plugins: [../..]
tags: [python, review, none]
---
Can you review this before I merge it? It's the renewal step of our subscription service.

```python
import json
import logging
from dataclasses import dataclass
from datetime import timedelta

logger = logging.getLogger(__name__)

RENEWAL_PERIOD = timedelta(days=30)


@dataclass(frozen=True)
class Charge:
    id: str
    amount_cents: int
    currency: str


class RenewalService:
    def __init__(self, repository, billing, ledger_path):
        self.repository = repository
        self.billing = billing
        self.ledger_path = ledger_path

    def renew(self, subscription_id, plan_code, customer_email, amount_cents, currency, renewed_on, send_receipt):
        subscription = self.repository.get(subscription_id)
        if subscription is None:
            raise LookupError(f"subscription {subscription_id} not found")

        charge = self.billing.charge(customer_email, amount_cents, currency)
        subscription.plan_code = plan_code
        subscription.paid_until = max(subscription.paid_until, renewed_on) + RENEWAL_PERIOD
        self.repository.save(subscription)
        self._record_in_ledger(subscription_id, charge)

        if send_receipt:
            self.billing.send_email(customer_email, build_receipt(charge))
        logger.info("renewed %s until %s", subscription_id, subscription.paid_until)
        return subscription

    def _record_in_ledger(self, subscription_id, charge):
        entry = {
            "subscription_id": subscription_id,
            "charge_id": charge.id,
            "amount_cents": charge.amount_cents,
            "currency": charge.currency,
        }
        try:
            with open(self.ledger_path, "a", encoding="utf-8") as ledger:
                ledger.write(json.dumps(entry) + "\n")
        except:
            pass


def build_receipt(charge, lines=[]):
    lines.append(f"Charge {charge.id}: {charge.amount_cents / 100:.2f} {charge.currency.upper()}")
    return "\n".join(lines)
```
