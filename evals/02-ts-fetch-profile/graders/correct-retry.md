---
type: llm
focus:
  source: file
  path: fetchUserProfile.ts
---
The file loads a user profile over HTTP. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (network errors, backoff delays, malformed JSON) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. It requests `GET /api/users/<id>` with the global `fetch`, putting the given id in the path.
2. A 5xx response is retried, with at most 3 retries after the first attempt (3 attempts in total is also acceptable).
3. A non-OK response that is not 5xx fails at once without retrying, by throwing or by returning an explicit error value.
4. When the retries run out, the caller gets an error (thrown or returned), never `undefined`, `null`, or a partial profile.
5. The returned profile maps `created_at` to a `createdAt` property holding a `Date`.
6. The profile has a declared type (interface or type alias) used in the function's return type.
