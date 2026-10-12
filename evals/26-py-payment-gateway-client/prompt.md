---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, none]
---
Write `payments/gateway_client.py`, the client our checkout code uses to talk to our payment provider over HTTP with `httpx`. It needs to charge a card and refund a charge. The provider's API:

- `POST {base_url}/v1/charges` with JSON `{"amount": 1999, "currency": "usd", "source": "<card token>"}` and an `Idempotency-Key` header. Success is 201 with `{"id": "ch_123", "status": "succeeded"}`. A declined card is 402 with `{"error": {"code": "card_declined", "message": "..."}}`.
- `POST {base_url}/v1/refunds` with JSON `{"charge": "ch_123", "amount": 1999}`. Success is 201 with `{"id": "re_456", "status": "succeeded"}`; 404 means the charge doesn't exist.
- Every request sends `Authorization: Bearer <api key>`. A 429 or any 5xx means the provider is temporarily unavailable.

Checkout must not have to know about httpx or HTTP status codes: whatever goes wrong, it should only ever see our own errors for a declined card, an unknown charge, the provider being unavailable, or any other failure.
