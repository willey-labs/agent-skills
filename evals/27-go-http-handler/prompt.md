---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [go, write, go-http]
---
Write `internal/signup/handler.go` for our Go service (plain `net/http`, no router library). It's the handler for `POST /signup`: it decodes a JSON body with `email`, `password` and `display_name`, validates it, and creates the account through a store the handler is given when it's constructed. Declare the store interface in the same file, with one method that takes the request context and the new account and returns the new user's ID. The store returns `ErrEmailTaken` when the email is already registered; declare that error in the file too.

Validation: the email must contain `@`, the password must be at least 12 characters, and the display name must be 1 to 50 characters after trimming surrounding spaces.

Responses: `201` with `{"id": "<new id>"}` on success, `400` when the body isn't valid JSON or a field fails validation (say which field), `409` when the email is taken, and `500` for any other store failure.
