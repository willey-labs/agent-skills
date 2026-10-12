---
type: llm
focus:
  source: file
  path: payments/gateway_client.py
---
The file is a client for a payment provider's HTTP API, built on `httpx`. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (retries, timeout lengths, logging, how idempotency keys are made, the shape of the success value, whether the errors live in this file or another module of the package) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. Charging POSTs to `/v1/charges` with `amount`, `currency` and `source` in the JSON body and an `Idempotency-Key` header, and on 201 gives the caller the charge id.
2. Refunding POSTs to `/v1/refunds` with `charge` and `amount` in the JSON body, and on 201 gives the caller the refund id.
3. Every request sends `Authorization: Bearer <api key>`.
4. A 402 from the charge call becomes the client's own card-declined error, carrying the provider's decline code or message.
5. A 404 from the refund call becomes the client's own unknown-charge error.
6. A 429, any 5xx, a timeout and a connection failure become the client's own provider-unavailable error (retrying first is fine).
7. Any other non-success status becomes one of the client's own errors.
8. No `httpx` exception can reach the caller of the charge or refund operation, and neither can the `ValueError` (including `json.JSONDecodeError`) or `KeyError` that decoding or reading the response JSON raises on a malformed success or error body.
