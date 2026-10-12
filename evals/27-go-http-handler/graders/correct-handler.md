---
type: llm
focus:
  source: file
  path: internal/signup/handler.go
---
The file is a `net/http` handler for `POST /signup`. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (unknown JSON fields, HTTP method checks, logging, the wording of error bodies beyond naming the field) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The body is decoded as JSON into a value with `email`, `password` and `display_name` fields; a body that fails to decode gets `400` and the handler stops there.
2. Validation answers `400` with a message naming the field for: an email without `@`; a password shorter than 12 characters; a display name that is empty or longer than 50 characters after trimming surrounding spaces. Counting bytes or runes both pass.
3. The store reaches the handler when it is constructed (a struct field or a closure variable, not a package-level variable) and is typed as an interface whose one method takes a `context.Context`; the handler passes it the request's context.
4. Only a request that passed validation reaches the store.
5. A store error that is `ErrEmailTaken` (checked with `errors.Is` or `==`) gets `409`, any other store error gets `500`, and after writing an error status the handler returns without writing a success response.
6. On success the status is `201` and the JSON body holds the new ID under the key `id`.
