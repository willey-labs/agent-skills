# Go (HTTP services) — Structure

## Builds on `common/structure.md`

This file adds only what's specific to Go HTTP services (Gin, Echo, Fiber, chi, gorilla/mux, or plain
`net/http`). The decomposition model — business → feature → sub-feature → unit, one job per file, variants
as one-interface-per-form, all the ST rules — lives in `common/structure.md`, loaded alongside this. Go's
idioms line up with it: `internal/` enforces cross-tree visibility at compile time (ST-003), and a
package's exported identifiers are its front door (ST-002). Read that first.

## Outer shell

Two top folders are yours to fill:

- `cmd/<binary>/main.go` — one folder per binary (`cmd/api/`, `cmd/worker/`). `main.go` stays small: load
  config, wire dependencies, start the server. It reads as a manifest of features, not as logic.
- `internal/` — one package per feature (`internal/<feature>/`, `internal/<other-feature>/`). Each feature owns its
  handlers, service, persistence, and types together. The package **name** is the capability noun, matching
  the folder (`internal/<feature>/` → `package <feature>`); that is ST-001 in Go form. Shared infrastructure that
  three or more features use rises to `internal/platform/<thing>/` (the lowest covering level, ST-004).

`internal/` is special: a package under it can only be imported by code in the same module rooted at the
parent of `internal/`. That is **compile-time** privacy, not convention. Nest it again
(`internal/<feature>/internal/...`) to keep a feature's sub-packages private to that feature. `pkg/` is only
for code meant to be imported by *other* modules — most services never need it. Top-level `models/`,
`services/`, or `handlers/` packages are filing by kind (ST-001) — forbidden.

## Naming

- **Files** — `snake_case.go` (`<verb>_<noun>.go`, `service.go`). Tests are `<source>_test.go`, co-located.
- **Packages** — short, lowercase, no underscores; the capability noun (`<feature>`).
- **Avoid stuttering**: `<feature>.<Entity>` is idiomatic, but `<feature>.<Entity>Service` stutters — the
  package already qualifies the type, so it's `<feature>.Service`.
- Sentinel errors are `Err<Specific>` (`ErrNotFound`). Constructors are `New<Type>` (`NewService`).
  Request/response DTOs are `<Verb><Resource>Request` / `<Resource>Response`.

## Front door

A package's public surface is simply its **exported (capitalized) identifiers**; everything lowercase is
private to the package, and `internal/` makes the package itself invisible outside its subtree. That is
Go's built-in front door — there is no `index` file. Other features depend on those exported names (and
preferably on a consumer-defined interface, see below), never on internals.

## Go specifics

- **Handlers are thin.** A handler parses the request, calls `svc.Method(ctx, ...)`, and writes the
  response. No SQL and no branching on business state inside a handler — push any business check down into
  the service.

- **Errors are values; never swallow.** Define **sentinel errors per feature** (`errors.go`) for
  the failures callers branch on. **Wrap raw infrastructure errors at the boundary** with
  `fmt.Errorf("scope: %w", err)` so the cause is preserved and `pgx.ErrNoRows` / `sql.ErrNoRows` never bubble
  out of the repository. **Translate error → HTTP status INSIDE the feature package**, calling a generic
  `httpx`-style helper. Never put the mapping in shared `httpx`: if `httpx` switched on `<feature>.ErrNotFound`
  it would import `<feature>`, but `<feature>` already imports `httpx` — an import cycle Go refuses to compile.
  Each feature owns its own translation. Forbidden: `if err != nil { _ = err }`, returning a bare `nil`, or
  `panic()` for ordinary failure.

- **`context.Context` is the first arg of anything that does I/O.** Pass the request's context from
  handler through service to repository. Never `context.Background()` in business code — it drops deadlines,
  cancellation, and per-request values (request ID, trace span).

- **Config loaded once, typed, validated at boot.** One typed struct, populated in `main.go`;
  missing required values make startup fail fast. Forbidden: `os.Getenv` scattered through feature packages.

- **Interfaces are defined by the consumer, not the producer.** The service that needs a dependency
  declares the small interface it requires, beside its own code; the provider satisfies it implicitly (no
  `implements` keyword). This keeps each package self-describing. Forbidden: a `BaseRepository` /
  `BaseService` interface every feature implements (generic name, ST-006, and a shape they don't share).

- **No DI container; constructors take their dependencies.** Wire them by hand in `main.go` —
  explicit, refactorable, grep-friendly. If the wiring grows unwieldy, give each feature a
  `New<Feature>Module(...)` constructor returning its service and route registrar, so `main.go` becomes a
  list of module constructors. Reach for code-gen wiring only when manual wiring genuinely hurts.

- **Database access.** Whatever the tool (`database/sql`, `sqlx`, `sqlc`, `pgx`, an ORM), the
  feature's **repository file owns all of its SQL** — service code never queries the DB directly. Migrations
  live in `migrations/`, are run by a migration tool at deploy time (not on startup, outside tiny projects),
  and are append-only — never edit a merged migration.
