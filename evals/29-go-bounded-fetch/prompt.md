---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [go, write, none]
---
Write `internal/fetch/fetch.go`: a Go function that downloads the bodies of a list of URLs concurrently, using an `*http.Client` the caller provides, with a cap on how many requests are in flight at once (the caller sets the cap). Return one result per URL in the same order as the input, each holding either the body or that URL's error; one URL failing must not stop the others. A non-2xx status counts as an error for that URL. If the caller's context is cancelled, abandon the requests in flight, start no new ones, and give every URL that didn't finish the context's error.
