---
type: llm
focus:
  source: file
  path: src/subscriptions/subscriptions.service.ts
---
The file is a NestJS service that creates and cancels subscriptions. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (how the repository stores data, listing subscriptions, the wording of error messages) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The repository and the clock arrive through the constructor as injected dependencies (an `@Inject` token, or an abstract class used as the provider token); the service does not construct them, and it reads the current time only from the clock, never from `new Date()` or `Date.now()`.
2. Creating asks the repository whether the customer already has an active subscription and, if so, throws an error that signals a conflict: Nest's `ConflictException`, or a domain error named for the conflict that the controller or an exception filter maps to 409.
3. Otherwise creating saves and returns a subscription with a new id, the given `customerId` and `planId`, status `active`, `startedAt` from the clock and `cancelledAt` null.
4. Cancelling an id the repository doesn't have throws `NotFoundException` (or a domain not-found error), and cancelling a subscription whose status is already `cancelled` throws a conflict error as in claim 2.
5. Otherwise cancelling sets status `cancelled` and `cancelledAt` from the clock, saves the change through the repository, and returns the updated subscription.
