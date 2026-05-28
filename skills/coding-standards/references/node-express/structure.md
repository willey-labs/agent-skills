# Node.js (Express / Fastify) — Architecture

The chosen pattern for plain Node.js backends using Express or Fastify (not NestJS): **package by feature** — top-level folders are business features, each containing its own route, service, repository, and types. Without a framework that imposes module structure (like NestJS), the pattern is even more important — discipline is the only enforcement.

---

## The philosophy in one sentence

> One folder per business feature, containing the route, service, repository, and types it needs. Cross-feature dependencies go through public APIs. `shared/` holds infrastructure used by three or more features.

---

## Mandatory shape

```
src/
  server.ts                         ← bootstrap (express/fastify app, listens)
  app.ts                            ← composition: registers feature routers + shared middleware

  checkout/                         ← 🛒 FEATURE
    checkout.routes.ts              ← express Router / fastify plugin
    checkout.service.ts             ← orchestration / use cases
    checkout.repository.ts          ← persistence
    checkout.schema.ts              ← request/input validation schema
    checkout.types.ts               ← feature-local types
    checkout.service.test.ts        ← test co-located
    index.ts                        ← 🚪 public API

  auth/                             ← 🔐 FEATURE
    auth.routes.ts
    auth.service.ts
    auth.middleware.ts              ← jwt verification middleware (exported via index.ts)
    auth.schema.ts
    auth.types.ts
    index.ts

  products/
    products.routes.ts
    products.service.ts
    products.repository.ts
    products.schema.ts
    products.types.ts
    index.ts

  shared/                           ← cross-cutting only (3+ features)
    db/
      client.ts                     ← database / ORM client
      index.ts
    middleware/
      error-handler.ts
      request-logger.ts
      rate-limit.ts
      index.ts
    logger/
      index.ts                      ← logger wrapper
    config/
      env.ts                        ← typed env access (validated at boot)
      index.ts
    errors/
      app-error.ts                  ← base error class
      not-found-error.ts
      validation-error.ts
      index.ts
    types/
      global.ts                     ← only truly app-wide types
```

---

## NDE-001 — One feature, one folder, everything inside

Each feature folder contains every layer it needs: route, service, repository, schema, types. To work on "checkout," you open one folder. To delete the feature, you delete one folder.

| Allowed at the top of `src/` | Forbidden |
|---|---|
| ✅ `server.ts`, `app.ts` | ❌ `controllers/` (or `routes/` collecting every route) |
| ✅ Feature folders | ❌ `services/` |
| ✅ `shared/` | ❌ `repositories/` |
|  | ❌ `models/`, `dtos/`, `validators/` as top-level |

A `src/routes/` folder containing every feature's routes means each feature is spread across `routes/`, `services/`, `repositories/`, `models/` — and adding a feature touches four folders. That's package-by-layer.

---

## NDE-002 — Routes are thin; services own use cases

The route file maps HTTP routes to handlers; the handler validates input and delegates to a service. **No business logic in the route layer.**

```ts
// ✅ Good — thin Express route, service does the work
// checkout/checkout.routes.ts
import { Router } from 'express'
import { placeOrderSchema } from './checkout.schema'
import { checkoutService } from './checkout.service'

const router = Router()

router.post('/orders', async (req, res, next) => {
  try {
    const input = placeOrderSchema.parse(req.body)
    const order = await checkoutService.placeOrder(input)
    res.status(201).json({ data: order })
  } catch (err) {
    next(err)
  }
})

export { router as checkoutRouter }
```

```ts
// ❌ Bad — route has business logic + raw DB access
router.post('/orders', async (req, res) => {
  const items = req.body.items                        // no validation
  if (items.length === 0) return res.status(400).send('empty')   // business rule in route
  const total = items.reduce((s, i) => s + i.price * i.qty, 0)   // calculation in route
  await db.query('INSERT INTO orders ...')            // direct DB in route
  res.status(201).send({ ok: true })
})
```

---

## NDE-003 — Services orchestrate; repositories persist

The same three-layer split as NestJS and the C# Application/Infrastructure pattern, but lighter — no DI container, just imports.

| Layer | Owns | Does NOT own |
|---|---|---|
| **Route** | HTTP plumbing, input parsing/validation, response shaping | Business rules, DB access |
| **Service** | Orchestration: validate, call repository, raise events | HTTP, direct SQL/ORM calls |
| **Repository** | Persistence per aggregate (not per table) | Business rules |

```ts
// checkout/checkout.service.ts
import { checkoutRepository } from './checkout.repository'
import type { PlaceOrderInput, Order } from './checkout.types'

export const checkoutService = {
  async placeOrder(input: PlaceOrderInput): Promise<Order> {
    if (input.items.length === 0) throw new ValidationError('empty_order')

    const order = await checkoutRepository.create(input)
    // raise event, log, etc.
    return order
  },
}

// checkout/checkout.repository.ts
import { db } from '@/shared/db'
import type { Order, PlaceOrderInput } from './checkout.types'

export const checkoutRepository = {
  async create(input: PlaceOrderInput): Promise<Order> {
    return db.order.create({ data: input })
  },
}
```

**Smell:** route doing `await db.query(...)` directly. The service and repository layers are missing — insert them.

---

## NDE-004 — Validation at the boundary

Express/Fastify give you no validation. Use a schema validator at the boundary so the rest of the code can trust its inputs. Pick whichever library fits the project — what matters is that:

- The schema lives in `<feature>.schema.ts`.
- The schema infers (or otherwise exposes) a TypeScript type so the route, service, and repository agree on the shape.
- The route validates **before** calling the service. No service method ever accepts `unknown` or raw `req.body`.

```ts
// checkout/checkout.schema.ts — sketch; use your preferred validator
export const placeOrderSchema = /* validator definition */;
export type PlaceOrderInput  = /* inferred or hand-written type */;

// checkout/checkout.routes.ts
router.post('/orders', async (req, res, next) => {
  const input = parseWithSchema(placeOrderSchema, req.body);   // throws ValidationError on failure
  const order = await checkoutService.placeOrder(input);
  res.status(201).json({ data: order });
});
```

If validation fails, throw a typed `ValidationError` and let the central error handler return 400 (see NDE-007). Don't sprinkle `res.status(400)` calls through route bodies.

---

## NDE-005 — `index.ts` is the public API of the feature

A feature exposes only what other features (or `app.ts`) need to wire it up — typically its router and a small selection of middleware/services.

```ts
// auth/index.ts
export { authRouter } from './auth.routes'
export { requireAuth } from './auth.middleware'
export type { AuthenticatedRequest } from './auth.types'
// auth.service.ts, auth.repository.ts, internal types stay private
```

```ts
// ✅ Allowed elsewhere
import { authRouter, requireAuth } from '@/auth'

// ❌ Forbidden — deep import past the public API
import { authService } from '@/auth/auth.service'
```

`app.ts` is the only place where every feature's router is mounted:

```ts
// app.ts
import express from 'express'
import { checkoutRouter } from '@/checkout'
import { authRouter, requireAuth }  from '@/auth'
import { productsRouter } from '@/products'
import { errorHandler, requestLogger } from '@/shared/middleware'

const app = express()
app.use(requestLogger)
app.use(express.json())

app.use('/auth', authRouter)
app.use('/products', productsRouter)
app.use('/checkout', requireAuth, checkoutRouter)

app.use(errorHandler)   // last
export { app }
```

---

## NDE-006 — `shared/` requires three users

Rule of Three applies. `shared/` is for cross-cutting infrastructure used by three or more features:

| Allowed in `shared/` | Forbidden |
|---|---|
| ✅ `shared/db/` — database / ORM client | ❌ `shared/utils.ts` |
| ✅ `shared/middleware/` — error handler, request logger, rate limiter | ❌ A "shared" middleware only one feature uses |
| ✅ `shared/logger/` — logger wrapper | ❌ Mega-file `shared/types.ts` |
| ✅ `shared/config/env.ts` — typed env validated once | ❌ Feature-specific service masquerading as shared |
| ✅ `shared/errors/` — base error class + common variants |  |

Logger and env should be **imported once at startup** and exposed as typed modules. Validate env at boot with whichever schema validator the project uses — never read `process.env.X` directly inside feature code.

---

## NDE-007 — Centralized error handling, structured errors

Each error has a class with a stable code and HTTP status. Routes never call `res.status(400).send(...)` directly — they `throw new ValidationError(...)` and let the central error handler translate it.

```ts
// shared/errors/app-error.ts
export abstract class AppError extends Error {
  abstract readonly code: string
  abstract readonly status: number
}

export class ValidationError extends AppError {
  readonly code = 'validation_error'
  readonly status = 400
}

export class NotFoundError extends AppError {
  readonly code = 'not_found'
  readonly status = 404
}
```

```ts
// shared/middleware/error-handler.ts — registered LAST in app.ts
import type { ErrorRequestHandler } from 'express'
import { AppError } from '@/shared/errors'
import { logger } from '@/shared/logger'

export const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  if (err instanceof AppError) {
    res.status(err.status).json({ error: { code: err.code, message: err.message } })
    return
  }
  logger.error({ err }, 'unhandled error')
  res.status(500).json({ error: { code: 'internal_error' } })
}
```

This is the runtime version of `error-handling.md` EH-002 — translate raw exceptions at the boundary; never let them leak as 500s.

---

## NDE-008 — Async/await + a single error path

Old Node (Express callbacks) is forbidden in new code. Every route handler is `async`; thrown errors propagate to `next(err)` (Express 5 does this automatically; in Express 4 wrap with `try/catch (err) { next(err) }` or use an `asyncHandler` helper).

```ts
// ✅ Express 5 — thrown async errors flow to error handler
router.post('/orders', async (req, res) => {
  const input = placeOrderSchema.parse(req.body)
  const order = await checkoutService.placeOrder(input)
  res.status(201).json({ data: order })
})

// ✅ Express 4 — wrap to get the same behavior
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next)
router.post('/orders', asyncHandler(async (req, res) => { ... }))
```

**Fastify** handles async routes natively — return a value or throw; the framework does the rest.

---

## NDE-009 — Naming

| Type | Convention | Example |
|---|---|---|
| Feature folder | `kebab-case`, plural noun | `checkout/`, `products/`, `auth/` |
| Route file | `<feature>.routes.ts` | `checkout.routes.ts` |
| Service | `<feature>.service.ts` | `checkout.service.ts` |
| Repository | `<feature>.repository.ts` | `checkout.repository.ts` |
| Schema | `<feature>.schema.ts` | `checkout.schema.ts` |
| Middleware | `<feature>.middleware.ts` | `auth.middleware.ts` |
| Types | `<feature>.types.ts` | `checkout.types.ts` |
| Test | `<file>.test.ts` | `checkout.service.test.ts` |
| Exported service object | camelCase singular | `checkoutService`, `authService` |
| Exported router | camelCase + `Router` | `checkoutRouter` |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Top-level `routes/`, `services/`, `repositories/` folders | Package by layer — feature spread across folders |
| Route handlers with business logic or direct DB calls | Should delegate to service + repository |
| Unvalidated `req.body` reaching a service | Validate at the boundary with a schema |
| `res.status(400).send(...)` scattered through routes | Throw a typed error; let the central handler respond |
| `process.env.X` scattered through feature code | Validate once at boot in `shared/config/env.ts` |
| Cross-feature deep imports (`from '@/auth/auth.service'`) | Should go through `@/auth` (index.ts) |
| `shared/utils.ts` or `shared/helpers.ts` | Junk drawer |
| Synchronous callbacks (Express style from 2014) | All handlers must be async |
| Generic repository (`Repository<T>`) serving every feature | One repository per feature/aggregate, with domain-shaped methods |
| Returning ORM entity types directly from routes | Couples API to DB schema; map to a response shape at the boundary |

---

## Review checklist

```
Structure
  □ Top-level folders are features, not technical layers
  □ Each feature has *.routes, *.service, *.repository, *.schema, *.types
  □ Each feature has index.ts as public API
  □ shared/ contains only code used by 3+ features

Routes
  □ Thin — parse input, call service, shape response
  □ Use schema validation at the boundary
  □ Throw typed errors; never raw res.status().send()

Services / Repositories
  □ Services orchestrate, don't talk SQL/ORM directly
  □ One repository per feature/aggregate, with domain-shaped methods
  □ Repositories never imported by routes — only by services

Cross-cutting
  □ Env validated once at boot
  □ Logger imported from shared/, not console.log
  □ Error handler registered last in app.ts
  □ All handlers async; errors flow to error handler

Imports
  □ Cross-feature imports go through index.ts
  □ No deep imports past a feature's index.ts
```
