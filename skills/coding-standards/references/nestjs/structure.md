# NestJS — Architecture

The chosen pattern for NestJS projects: **package by feature** — top-level folders are business features, each containing all its layers (controller, service, repository, dto, entity). NestJS's `Module` concept aligns naturally with this: one folder = one module = one feature.

---

## The philosophy in one sentence

> One folder per business feature, containing every layer that feature needs. Modules align to folders. Cross-feature dependencies go through public interfaces, not internals.

---

## Mandatory shape

```
src/
  app.module.ts                      ← composition root
  main.ts                            ← bootstrap

  checkout/                          ← 🛒 FEATURE
    checkout.module.ts               ← NestJS module
    checkout.controller.ts           ← HTTP handlers
    checkout.service.ts              ← orchestration / use cases
    checkout.repository.ts           ← persistence (or *.repository.ts per aggregate)
    checkout.gateway.ts              ← websocket / external API (when needed)
    dto/
      create-order.dto.ts
      update-order.dto.ts
    entities/
      order.entity.ts
      order-item.entity.ts
    guards/
      checkout-owner.guard.ts        ← when used by only this feature
    pipes/
      validate-card.pipe.ts
    checkout.controller.spec.ts
    checkout.service.spec.ts
    index.ts                         ← public API (what other features may import)

  auth/                              ← 🔐 FEATURE
    auth.module.ts
    auth.controller.ts
    auth.service.ts
    strategies/
      jwt.strategy.ts
      local.strategy.ts
    guards/
      jwt-auth.guard.ts              ← used by many features → exported
    decorators/
      current-user.decorator.ts
    dto/
    entities/
      user.entity.ts
    index.ts

  shared/                            ← cross-cutting only (3+ features)
    database/
      database.module.ts
      database.providers.ts
    logger/
      logger.module.ts
      logger.service.ts
    config/
      config.module.ts
      env.validation.ts
    filters/
      http-exception.filter.ts
    interceptors/
      logging.interceptor.ts
      transform.interceptor.ts
```

---

## NST-001 — One feature, one module, one folder

Each feature folder must contain its own `*.module.ts`. The module declares everything that feature owns:

```ts
// checkout/checkout.module.ts
@Module({
  imports: [DatabaseModule, AuthModule],
  controllers: [CheckoutController],
  providers: [CheckoutService, CheckoutRepository],
  exports: [CheckoutService],          // ← public surface, gated by index.ts
})
export class CheckoutModule {}
```

**Test:** `rm -rf src/checkout/` should remove the feature cleanly (assuming no other feature has crept into importing its internals — which NST-005 forbids).

---

## NST-002 — No top-level technical folders

| Allowed at the top of `src/` | Forbidden |
|---|---|
| ✅ `app.module.ts`, `main.ts` | ❌ `controllers/` |
| ✅ Feature folders (`checkout/`, `auth/`, `products/`) | ❌ `services/` |
| ✅ `shared/` | ❌ `repositories/` |
|  | ❌ `dtos/`, `entities/`, `models/` as top-level |

A `src/controllers/` folder means every feature is spread across `controllers/`, `services/`, `repositories/`... to work on checkout, you touch six folders. That's package-by-layer — the anti-pattern.

---

## NST-003 — Layer files inside the feature follow Nest conventions

Inside a feature folder, file naming follows Nest's official convention (`*.controller.ts`, `*.service.ts`, etc.). Group by **kind** only when there are multiple of the same kind:

| Single | Multiple |
|---|---|
| `checkout.controller.ts` | `dto/` folder with multiple DTOs |
| `checkout.service.ts` | `entities/` folder with multiple entities |
| `checkout.repository.ts` | `strategies/` folder with multiple Passport strategies |

Don't create a `services/` folder just to hold one service file. Don't create a `dto/` folder for a single DTO; promote it when the second one arrives.

---

## NST-004 — `index.ts` is the public API

A feature may export selected providers, types, decorators, or guards. **Everything else stays private** to the feature.

```ts
// auth/index.ts
export { AuthService } from './auth.service'
export { JwtAuthGuard } from './guards/jwt-auth.guard'
export { CurrentUser } from './decorators/current-user.decorator'
export type { JwtPayload } from './types'
// auth.controller.ts, strategies/, dto/ stay private
```

```ts
// ✅ Allowed from another feature
import { JwtAuthGuard } from '@/auth'

// ❌ Forbidden — deep import past the public API
import { JwtAuthGuard } from '@/auth/guards/jwt-auth.guard'
```

**Module export gating:** what's in the module's `exports: []` array is the runtime surface; what's in `index.ts` is the import-time surface. Keep them aligned — if `AuthService` isn't in module `exports`, it can't be injected elsewhere, so it shouldn't be in `index.ts` either.

---

## NST-005 — Features depend on `shared/`, not on each other (mostly)

Cross-feature dependencies are allowed but **only through the public API** (`index.ts`). Most features should depend only on `shared/` and on a small set of stable foundational features (typically `auth/`, `users/`).

```
auth/, users/    ← foundational, can be depended on by anyone
  ↑
business features → import from shared/, and from foundationals via index.ts
  ↑
app.module       → composes all features
```

**The smell:** feature A's controller imports a service from feature B's `services/` folder. That's a deep import bypassing the public API. Fix by exporting from B's `index.ts` (and B's module `exports`), or by extracting the shared piece into `shared/`.

---

## NST-006 — `shared/` requires three users (Rule of Three)

`shared/` exists for cross-cutting infrastructure used by 3+ features:

| Allowed in `shared/` | Forbidden |
|---|---|
| ✅ `shared/database/` — ORM / database client module | ❌ `shared/utils.ts` |
| ✅ `shared/logger/` — logger wrapper | ❌ `shared/types.ts` mega-file |
| ✅ `shared/config/` — env validation, ConfigModule | ❌ Feature-coupled code with a generic name |
| ✅ `shared/filters/` — global exception filters | ❌ Code only one or two features use |
| ✅ `shared/interceptors/` — logging, transform, cache |  |
| ✅ `shared/pipes/` — global validation, parsing |  |

**Promotion process:**

1. First use → inside the feature.
2. Second use in another feature → duplicate (duplication is acceptable at two).
3. Third use → extract to `shared/`.

---

## NST-007 — Domain in entities; orchestration in services; HTTP in controllers

Nest's layer separation is conventional but worth enforcing:

| Layer | Owns | Does NOT own |
|---|---|---|
| **Controller** | HTTP concerns (route binding, DTO validation, status codes) | Business rules, database access |
| **Service** | Orchestration: validates pre-conditions, coordinates repos, raises domain events | Direct DB queries (delegate to repository), HTTP details |
| **Repository** | Persistence per feature/aggregate (not per table) — domain-shaped methods | Business rules |
| **Entity** | Domain invariants, business behavior (`order.cancel()`), value objects | Persistence concerns, framework decorators in the **domain core** (acceptable on the persistence-facing entity) |

**Smell:** a controller that does `await repo.findOne(...)` and `await repo.save(...)` directly. The service layer is missing. Insert it.

**Smell:** a service with `if (a) await db.x() else await db.y()` and no domain entity behavior — anemic services with anemic entities. Push behavior down onto entities where it belongs.

---

## NST-008 — DTOs at the controller boundary; entities inside

DTOs are the wire shape. Entities are the domain shape. They are not the same and should not be conflated.

```ts
// dto/create-order.dto.ts — wire shape, validated at the boundary
export class CreateOrderDto {
  @IsArray() @ValidateNested({ each: true })
  items!: OrderItemInput[]

  @IsString() @IsUUID()
  customerId!: string
}

// entities/order.entity.ts — domain shape, owns invariants
export class Order {
  static place(customerId: CustomerId, items: OrderItem[]): Order { ... }
  cancel(reason: string): void { ... }
}
```

**Forbidden:** returning entities directly from controllers (leaks internal shape and persistence concerns). **Transform to a response DTO** at the controller boundary.

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Top-level `controllers/`, `services/`, `repositories/` folders | Package by layer — the anti-pattern this design replaces |
| Feature A importing from feature B's internals | Bypasses public API; tightly couples features |
| `shared/utils.ts` or `shared/helpers.ts` | Junk drawer |
| Controller doing direct DB calls | Skips the service layer; mixes HTTP and persistence |
| Anemic entities (data + no behavior) and fat services | Domain logic in the wrong place — see Objects & Data OD-001/OD-004 |
| Returning persistence entities from controllers | Leaks internal shape; couples API to DB schema |
| One module file importing 30 features | The composition root has become a god module — re-evaluate feature boundaries |

---

## Review checklist

```
Structure
  □ Top-level folders are features, not technical layers
  □ Each feature has its own *.module.ts
  □ Each feature has index.ts as public API
  □ shared/ contains only code used by 3+ features

Per feature
  □ Controllers handle HTTP only
  □ Services orchestrate; entities own behavior
  □ Repositories work per aggregate, not per table
  □ DTOs at the controller boundary; entities never returned directly

Imports
  □ Cross-feature imports go through index.ts
  □ Module exports list matches index.ts surface
  □ No deep imports past a feature's index.ts
```
