---
type: llm
focus:
  source: file
  path: src/app.ts
---
The file is an Express 4 app with one transfer route and a central error-handling middleware. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (transfers to the same account, decimal precision, the code and message strings, logging, malformed JSON bodies) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. It exports the app, registers `express.json()` and a `POST /transfers` route, and does not call `listen` unconditionally when the file is imported.
2. A domain error type (an `Error` subclass, with or without subclasses per failure) represents the three failures and carries what the middleware needs to pick the status code.
3. The route raises that domain error for each failure: 400 when an id is not a non-empty string or `amount` is not a positive number; 404 when either account is missing from the map; 409 when the source balance is less than the amount. The route never writes these error responses itself.
4. On success it subtracts the amount from the source account, adds it to the destination account, and responds 200 with both new balances.
5. Errors raised in the route reach the error middleware: the handler throws synchronously or passes the error to `next`. An `async` handler whose rejection is neither caught and passed to `next` nor wrapped by a helper that does so fails this claim.
6. One error-handling middleware with the four-parameter `(err, req, res, next)` shape is registered after the route; it responds with the domain error's status and `{ error: { code, message } }`, and with 500 and a generic message, not the original error's message, for any other error.
