# Go (HTTP services) — Architecture

The chosen pattern for Go HTTP services (Gin, Echo, Fiber, chi, gorilla/mux, or plain `net/http`): **package by feature** under `internal/`, where each feature owns its handlers, service, repository, and types. Cross-package boundaries are enforced by Go's `internal/` convention plus discipline. Errors are values; no exceptions; no DI container.

---

## The philosophy in one sentence

> One package per business feature under `internal/`. Each package owns handlers, service, repository, and types. Cross-package dependencies use exported identifiers only. Errors are returned, wrapped at boundaries, and centralized at the HTTP layer.

---

## Builds on `common/structure.md`

This file specializes the universal structural rules in `references/common/structure.md`. Go has its own idioms that align well with those rules: `internal/` enforces package privacy at compile time (ST-003); exported identifiers form the public surface (ST-002); the convention of small interfaces consumed close to where they're used. What this file adds: error wrapping for boundary translation, context-everywhere for cancellation, no DI container, and the `cmd/` + `internal/` layout. Read `common/structure.md` first.

---

## Mandatory shape

```
go.mod
go.sum
README.md

cmd/
  api/
    main.go                          ← server entrypoint: wires deps, starts http.Server
  worker/
    main.go                          ← optional: background worker entrypoint

internal/                            ← unexported to other modules (Go's privacy boundary)
  orders/                            ← 🛒 FEATURE package
    handler.go                       ← HTTP handlers (Gin/Echo/Fiber/chi)
    service.go                       ← orchestration / use cases
    repository.go                    ← persistence (SQL via sqlx/sqlc/pgx)
    types.go                         ← request/response/domain types
    errors.go                        ← feature-specific sentinel errors
    handler_test.go
    service_test.go

  catalog/
    handler.go
    service.go
    repository.go
    types.go
    errors.go

  identity/
    handler.go
    service.go
    auth.go                          ← JWT/session helpers
    types.go

  platform/                          ← shared infrastructure used by 3+ features
    db/
      postgres.go                    ← *sql.DB / *pgxpool.Pool factory
      migrations.go                  ← goose/golang-migrate runner
    httpx/
      middleware.go                  ← request logging, request ID, recover
      problem.go                     ← Problem Details responder
    config/
      config.go                      ← typed env loader (envconfig / viper)
    logger/
      logger.go                      ← zerolog / slog wrapper
    errors/
      errors.go                      ← AppError, error codes, HTTP mapping

pkg/                                 ← (rare) packages importable by OTHER Go modules
  goclient/                          ← only when you ship a client library

migrations/                          ← SQL migrations
  001_init.sql
  002_add_orders.sql

Dockerfile
Makefile
```

**Key Go-isms:**

- `internal/` is special: a package under `internal/` can only be imported by code in the same module rooted at the parent of `internal/`. This is **compile-time** privacy, not just convention.
- `cmd/<binary>/main.go` is the binary entrypoint. One folder per binary. `main.go` is small — it parses config, wires dependencies, starts the server.
- `pkg/` is for code intended to be imported by *other* Go modules. **Use sparingly.** Most teams don't need a `pkg/` folder.

---

## GO-001 — `cmd/` + `internal/` is the right top-level layout

`cmd/api/main.go` parses config, wires dependencies, and starts the HTTP server:

```go
// cmd/api/main.go
package main

import (
    "context"
    "log"
    "net/http"

    "example.com/myapp/internal/orders"
    "example.com/myapp/internal/identity"
    "example.com/myapp/internal/platform/config"
    "example.com/myapp/internal/platform/db"
    "example.com/myapp/internal/platform/httpx"
)

func main() {
    ctx := context.Background()

    cfg, err := config.Load()
    if err != nil {
        log.Fatalf("config: %v", err)
    }

    pool, err := db.NewPostgres(ctx, cfg.DatabaseURL)
    if err != nil {
        log.Fatalf("db: %v", err)
    }
    defer pool.Close()

    orderRepo := orders.NewRepository(pool)
    orderSvc := orders.NewService(orderRepo)

    identitySvc := identity.NewService(pool, cfg.JWTSecret)

    r := httpx.NewRouter()
    httpx.RegisterMiddleware(r)
    orders.RegisterRoutes(r, orderSvc)
    identity.RegisterRoutes(r, identitySvc)

    log.Printf("listening on :%d", cfg.Port)
    if err := http.ListenAndServe(cfg.Addr(), r); err != nil {
        log.Fatal(err)
    }
}
```

`main.go` reads as a manifest of features. It is short — the actual logic lives in each feature package.

---

## GO-002 — One feature per package; package name is the capability noun

Each feature lives in `internal/<feature>/`. Package name matches folder. `internal/orders/` has `package orders`.

The package owns:

| File | Purpose |
|---|---|
| `handler.go` | HTTP handlers + the `RegisterRoutes(r, svc)` function that wires them |
| `service.go` | Use-case orchestration |
| `repository.go` | Persistence — SQL queries, ORM calls |
| `types.go` | Domain types + request/response DTOs |
| `errors.go` | Feature-specific sentinel errors |
| `*_test.go` | Tests, co-located with the file under test |

**The package is the public surface.** Anything exported (capitalized) is callable from other packages; anything lowercase is private. That's Go's built-in `index.ts` mechanism — see `common/structure.md` ST-002.

```go
// internal/orders/service.go
package orders

type Service struct {
    repo *Repository
}

func NewService(repo *Repository) *Service { return &Service{repo: repo} }

// Place is the exported use case — other packages can call this via the Service.
func (s *Service) Place(ctx context.Context, req PlaceOrderRequest) (*Order, error) {
    if len(req.Items) == 0 {
        return nil, ErrEmptyOrder
    }
    order := newOrder(req)         // newOrder is lowercase — private
    if err := s.repo.Save(ctx, order); err != nil {
        return nil, fmt.Errorf("orders.Place: %w", err)
    }
    return order, nil
}
```

---

## GO-003 — Handlers are thin; the service does the work

The handler binds HTTP to the service. It parses the request, calls `svc.Method(ctx, ...)`, and writes the response. **No business logic in handlers.**

```go
// internal/orders/handler.go
package orders

import (
    "encoding/json"
    "net/http"

    "github.com/go-chi/chi/v5"
)

func RegisterRoutes(r chi.Router, svc *Service) {
    r.Route("/orders", func(r chi.Router) {
        r.Post("/", placeOrderHandler(svc))
        r.Get("/{id}", getOrderHandler(svc))
    })
}

func placeOrderHandler(svc *Service) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        var req PlaceOrderRequest
        if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
            httpx.Problem(w, http.StatusBadRequest, "invalid_json", err.Error())
            return
        }
        order, err := svc.Place(r.Context(), req)
        if err != nil {
            httpx.WriteError(w, err)        // centralized translation
            return
        }
        httpx.WriteJSON(w, http.StatusCreated, OrderResponseFrom(order))
    }
}
```

**Forbidden:** SQL queries inside the handler. **Forbidden:** branch on business state inside the handler. If a check is part of the business rule, push it down into the service.

---

## GO-004 — Errors are values; wrap at boundaries; never swallow

Go uses returned errors instead of exceptions. Apply `common/error-handling.md` EH-002 with Go's idioms:

**1. Define sentinel errors per feature** for the domain failures callers branch on:

```go
// internal/orders/errors.go
package orders

import "errors"

var (
    ErrNotFound      = errors.New("order not found")
    ErrEmptyOrder    = errors.New("order has no items")
    ErrAlreadyPlaced = errors.New("order already placed")
)
```

**2. Wrap raw infrastructure errors at the boundary** so callers see a meaningful error and the cause is preserved:

```go
func (r *Repository) FindByID(ctx context.Context, id OrderID) (*Order, error) {
    var o Order
    err := r.pool.QueryRow(ctx, `SELECT ... WHERE id = $1`, id).Scan(...)
    if err != nil {
        if errors.Is(err, pgx.ErrNoRows) {
            return nil, ErrNotFound
        }
        return nil, fmt.Errorf("orders.FindByID: %w", err)
    }
    return &o, nil
}
```

**3. Translate at the HTTP boundary** — one place per service maps error types to HTTP status codes:

```go
// internal/platform/httpx/errors.go
package httpx

func WriteError(w http.ResponseWriter, err error) {
    switch {
    case errors.Is(err, orders.ErrNotFound):
        Problem(w, 404, "not_found", err.Error())
    case errors.Is(err, orders.ErrEmptyOrder), errors.Is(err, orders.ErrAlreadyPlaced):
        Problem(w, 400, "invalid_state", err.Error())
    default:
        logger.Error(err)
        Problem(w, 500, "internal", "internal server error")
    }
}
```

**Forbidden:** `if err != nil { _ = err }` or `if err != nil { return nil }` — silent swallowing. Either handle the error, return it (usually wrapped), or `log.Error` it with the comment explaining why ignoring is correct here.

**Forbidden:** raw `pgx.ErrNoRows` or `sql.ErrNoRows` bubbling out of the package. Translate at the repository's exit. That's `common/error-handling.md` EH-002 in Go form.

---

## GO-005 — `context.Context` everywhere; cancellation is real

The first argument to every exported method that does I/O or anything that might block is `ctx context.Context`. Pass the request's context down through services and repositories. **Never** `context.Background()` deep in business code.

```go
// ✅ Good
func (s *Service) Place(ctx context.Context, req PlaceOrderRequest) (*Order, error) { ... }
func (r *Repository) Save(ctx context.Context, order *Order) error { ... }

// ❌ Bad — service uses context.Background() instead of the request's context
func (s *Service) Place(req PlaceOrderRequest) (*Order, error) {
    return r.pool.Exec(context.Background(), ...)   // ignores client cancellation, timeouts
}
```

Why: the request context carries deadlines (HTTP read timeout, gateway timeouts), cancellation signals (client disconnected), and per-request values (request ID, tracing span). Replacing it with `context.Background()` silently drops all that.

---

## GO-006 — Configuration loaded once, typed, validated at boot

Use `envconfig` (`github.com/kelseyhightower/envconfig`) or `viper` or hand-rolled — just centralize:

```go
// internal/platform/config/config.go
package config

import (
    "fmt"
    "github.com/kelseyhightower/envconfig"
)

type Config struct {
    Port        int    `envconfig:"PORT" default:"8080"`
    DatabaseURL string `envconfig:"DATABASE_URL" required:"true"`
    JWTSecret   string `envconfig:"JWT_SECRET" required:"true"`
}

func (c Config) Addr() string { return fmt.Sprintf(":%d", c.Port) }

func Load() (*Config, error) {
    var c Config
    if err := envconfig.Process("", &c); err != nil {
        return nil, fmt.Errorf("config: %w", err)
    }
    return &c, nil
}
```

**Forbidden:** `os.Getenv("X")` scattered through feature packages. Required env missing → `Load()` returns an error → `main.go` fails fast. That's the desired startup behavior.

---

## GO-007 — Interfaces defined by the consumer, not the producer

This is Go's strongest design idiom and it differs from most other languages. **Define interfaces where they are used, not where they are implemented.** A small, single-method interface declared in the service file communicates exactly what the service depends on:

```go
// internal/orders/service.go
package orders

// PaymentCharger is the interface the service needs. It is defined HERE because
// the service is the consumer. The billing package implements this implicitly by
// exposing a matching method; no `implements` keyword is needed in Go.
type PaymentCharger interface {
    Charge(ctx context.Context, orderID OrderID, amount Money) error
}

type Service struct {
    repo     *Repository
    payments PaymentCharger    // accepts anything that satisfies the interface
}

func NewService(repo *Repository, payments PaymentCharger) *Service {
    return &Service{repo: repo, payments: payments}
}
```

This keeps each package self-describing — you can read the service file and immediately see what it depends on, with no need to chase to another package for the interface definition. Tests pass in a fake; production passes in the real `*billing.Service`.

**Forbidden:** a `BaseRepository` or `BaseService` interface in `shared/` that every feature implements. That collapses to ST-006 (generic names) and forces all features to share one shape they don't actually share.

---

## GO-008 — No DI container; constructors take dependencies

Go has no Spring, no NestJS. Wire dependencies manually in `main.go`. That's fine — the wiring is explicit, refactorable, and grep-friendly.

```go
// cmd/api/main.go (excerpt)
orderRepo := orders.NewRepository(pool, logger)
billingClient := billing.NewClient(cfg.BillingURL, cfg.BillingKey)
orderSvc := orders.NewService(orderRepo, billingClient)
orders.RegisterRoutes(r, orderSvc)
```

If `main.go` grows past ~100 lines of wiring, **introduce a `wire.go` per feature** that has a `NewModule(pool *pgxpool.Pool, ...) *Module` returning a struct with the service and the route registrar:

```go
// internal/orders/wire.go
package orders

type Module struct {
    Service *Service
    Routes  func(chi.Router)
}

func NewModule(pool *pgxpool.Pool, payments PaymentCharger) *Module {
    repo := NewRepository(pool)
    svc := NewService(repo, payments)
    return &Module{
        Service: svc,
        Routes:  func(r chi.Router) { RegisterRoutes(r, svc) },
    }
}
```

`main.go` becomes a list of `NewModule(...)` calls — same readability as Spring Boot's `Map<X>Endpoints()` pattern.

For really large apps, Google's `wire` (`github.com/google/wire`) generates the wiring code from a small spec. Optional — don't reach for it until manual wiring genuinely hurts.

---

## GO-009 — Cross-feature dependencies are explicit

Capability `orders` calling capability `billing` happens through **exported identifiers and (preferably) consumer-defined interfaces**:

```go
// ❌ Forbidden — reaching into another package's internals
import "example.com/myapp/internal/billing/internal/legacy"

// ✅ Allowed — using the billing package's public surface
import "example.com/myapp/internal/billing"

// Even better — the orders service declares an interface and accepts an implementation
type PaymentCharger interface {
    Charge(ctx context.Context, orderID OrderID, amount Money) error
}
```

Go's `internal/` directories give you *another* level: a package at `internal/billing/internal/legacy/` is **only** importable from code under `internal/billing/...`. The compiler enforces this — there is no need for an extra linter. Use this to keep capability internals genuinely private.

---

## GO-010 — Naming

| Type | Convention | Example |
|---|---|---|
| Package | lowercase, short, singular noun (or domain plural) | `orders`, `billing`, `identity` |
| Exported type | `PascalCase` | `Order`, `Service`, `Repository` |
| Unexported type | `camelCase` | `placeOrderCommand`, `discountTable` |
| Exported function | `PascalCase` (verb) | `NewService`, `Place`, `RegisterRoutes` |
| Constructor | `New<Type>` | `NewService`, `NewRepository`, `NewPostgres` |
| Sentinel error | `Err<Specific>` | `ErrNotFound`, `ErrEmptyOrder` |
| Interface | adjective form, often `-er` | `Charger`, `Logger`, `Notifier` — *defined where used* |
| Constants | `PascalCase` if exported, `camelCase` if not | `MaxRetries`, `defaultTimeout` |
| Request DTO | `<Verb><Resource>Request` | `PlaceOrderRequest` |
| Response DTO | `<Resource>Response` | `OrderResponse` |
| Test file | `<source>_test.go` | `service_test.go` |
| Binary | `cmd/<name>/main.go` | `cmd/api/main.go`, `cmd/worker/main.go` |

**Avoid stuttering**: `orders.Order` is fine (idiomatic Go), but `orders.OrderService` is not — use `orders.Service`. The package name already qualifies the type.

---

## GO-011 — Database access patterns

For SQL, the project's choice is one of:

| Tool | Niche |
|---|---|
| `database/sql` + `pgx`/`mysql` driver + scanning helpers | Lightest weight; you write SQL by hand |
| `sqlx` | Like above, with struct scanning |
| `sqlc` | Generates type-safe Go code from SQL queries — current sweet spot for many teams |
| `pgx` + `pgxscan` | Postgres-only, performance-leaning |
| `gorm` / `ent` | Heavyweight ORMs — usually unnecessary, sometimes appropriate |

Whatever the tool, the **repository file** owns all SQL for the feature. Service code never calls `db.Query(...)` directly.

**Migrations** live in `migrations/` and are run by `goose`, `golang-migrate`, or `dbmate` at deploy time — not at app startup unless this is a very small project. Migrations are append-only; never edit a merged migration.

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Top-level `pkg/`, `models/`, `services/`, `handlers/` packages | Package by layer; use feature packages under `internal/` |
| Handlers running SQL queries directly | Use service + repository |
| Returning raw `pgx.ErrNoRows` / `sql.ErrNoRows` from a repository | Translate to a feature sentinel (`ErrNotFound`) at the boundary |
| `if err != nil { _ = err }` or silent ignore | Either handle or return a wrapped error |
| `context.Background()` inside business code | Use the request context |
| `os.Getenv` scattered through code | Load config once at startup |
| `interface{}` / `any` parameters where a typed struct would do | Loses type safety; rarely needed |
| `panic()` for ordinary failure | Use returned errors |
| Generic `Repository[T]` (or pre-generics `Repository`) interface | Each feature owns its repository with its own methods |
| `init()` functions that load config or open connections | Initialization belongs in `main.go`; `init()` is hard to test |
| Package-global state (`var DB *sql.DB`) | Pass dependencies in constructors |
| `pkg/utils/` or `pkg/helpers/` | Junk drawer |
| Importing another feature's `internal/` package | Compile error if used correctly, anti-pattern if escaped via go.mod replace |
| Stuttering identifiers (`orders.OrderService`) | Use `orders.Service` |

---

## Review checklist

```
Layout
  □ cmd/<binary>/main.go for each binary
  □ Each feature under internal/<feature>/ with handler/service/repository/types
  □ shared infrastructure under internal/platform/
  □ migrations/ at repo root; no auto-migrate on startup in production

Per feature package
  □ Handlers are thin; call service.Method(ctx, ...) and write response
  □ Services orchestrate; repositories own SQL
  □ Sentinel errors defined in errors.go (or top of service.go)
  □ Exported identifiers form the package's public surface

Errors
  □ Repository wraps raw driver errors into feature sentinels or fmt.Errorf("...: %w", err)
  □ HTTP boundary maps error → status (one centralized switch)
  □ No silent err drops
  □ No panic() for ordinary failure

Context
  □ ctx context.Context is the first arg of every I/O method
  □ Request context flows from handler through service through repository
  □ No context.Background() inside business code

Configuration
  □ Config loaded once in main.go via typed loader
  □ Required env produces a startup error
  □ No os.Getenv scattered through features

Interfaces
  □ Defined where consumed, not where implemented
  □ Small (1–3 methods typical)
  □ Per-feature repository (no BaseRepository)

Cross-feature
  □ Packages depend on each other via exported identifiers / consumer-side interfaces
  □ internal/<feature>/internal/ used for truly private sub-packages
  □ No imports of another feature's `internal/` subtree
```
