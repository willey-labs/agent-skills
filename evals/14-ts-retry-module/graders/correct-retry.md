---
type: llm
focus:
  source: file
  path: src/retry/withRetry.ts
---
The file exports a retry-with-exponential-backoff helper. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (a maximum of 0 or fewer attempts, negative delays, cancellation, jitter) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. `withRetry` is exported, accepts the operation, the maximum number of attempts, the base delay and the retry predicate, and returns a promise typed with the operation's own result type (generic, such as `Promise<T>`).
2. The operation is called at most the maximum number of attempts in total, counting the first call, and is not called again after it succeeds; a success resolves with the operation's result.
3. Before the n-th retry it awaits a timer-based delay of `baseDelay × 2^(n−1)` milliseconds: 100, 200, 400 for a base of 100.
4. When the predicate returns false for an error, that same error is thrown at once, with no wait and no further attempt.
5. When the last allowed attempt fails, the error from that attempt is thrown: the original error object, not a new or wrapped error, `undefined`, or a default value.
