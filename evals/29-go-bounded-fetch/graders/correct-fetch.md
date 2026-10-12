---
type: llm
focus:
  source: file
  path: internal/fetch/fetch.go
---
The file downloads a list of URLs concurrently with a cap on requests in flight. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (a cap of zero or less, an empty URL list, body size limits, retries) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. No more requests than the caller's cap run at once, enforced by a semaphore, a pool of that many workers, or `errgroup`'s `SetLimit`.
2. There is exactly one result per URL and result `i` always belongs to URL `i`, whatever order the requests finish in; goroutines store results without a data race (each writes only its own index of a pre-sized slice, or writes go through a mutex or channel).
3. A URL's failure (request error, non-2xx status, or body read error) is stored in that URL's result and neither cancels nor skips the other URLs.
4. Each request is built with the caller's context (`http.NewRequestWithContext` or `req.WithContext`), so cancelling it aborts requests in flight.
5. Once the context is cancelled, URLs not yet started are not fetched over the network (checking the context before starting, or calling `Do` with the cancelled context, which fails at once, both pass), and every URL that did not finish gets an error (the context's error or one wrapping it) rather than an empty success.
6. Every response body that was opened is closed.
7. The function returns only after every goroutine it started has finished.
