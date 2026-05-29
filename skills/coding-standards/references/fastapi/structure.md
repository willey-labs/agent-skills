# FastAPI — Architecture

The chosen pattern for FastAPI projects: **package by feature** — top-level folders are business features, each containing its own router, service, repository, schemas, and types. FastAPI imposes no structure of its own; this discipline is the only enforcement.

---

## The philosophy in one sentence

> One folder per business feature, containing the router, service, repository, Pydantic schemas, and types. Cross-feature dependencies go through the feature's public surface. `shared/` holds infrastructure used by 3+ features.

---

## Builds on `common/structure.md`

This file specializes the universal structural rules in `references/common/structure.md`. FastAPI is unopinionated about layout, so the universal rules apply hard. What we add here: APIRouter-per-feature, Pydantic at the boundary, the dependencies system, async hygiene, and the SQLAlchemy/SQLModel session pattern. Read `common/structure.md` first.

---

## Mandatory shape

```
src/myapp/
  main.py                              ← FastAPI app: creates app, mounts routers, lifespan
  __init__.py

  checkout/                            ← 🛒 FEATURE
    __init__.py                        ← declares the public surface
    router.py                          ← APIRouter — endpoint definitions
    service.py                         ← orchestration / use cases
    repository.py                      ← persistence
    schemas.py                         ← Pydantic input + output models
    models.py                          ← SQLAlchemy / SQLModel ORM models
    exceptions.py                      ← feature-specific exceptions
    dependencies.py                    ← FastAPI `Depends(...)` providers for this feature
    tests/
      test_router.py
      test_service.py

  identity/                            ← 🔐 FEATURE
    __init__.py
    router.py
    service.py
    schemas.py
    models.py
    auth.py                            ← JWT / OAuth wiring; provides current_user dependency
    dependencies.py

  products/
    ...

  shared/                              ← cross-cutting (3+ features)
    __init__.py
    db.py                              ← engine, session factory, get_session() dependency
    config.py                          ← Settings(BaseSettings) — typed env
    logging.py                         ← logger configuration
    errors.py                          ← AppError base + handlers
    middleware.py                      ← request logging, request ID
    pagination.py
    types.py                           ← only truly app-wide types
```

For very small projects, the per-feature layout can flatten to one file per feature (`checkout.py` containing router + service + schemas) — once a feature grows past ~150 lines, split into the folder layout above.

---

## FA-001 — One APIRouter per feature

Each feature exposes an `APIRouter` from its `router.py`:

```python
# checkout/router.py
from fastapi import APIRouter, Depends
from . import service, schemas
from ..identity.dependencies import current_user

router = APIRouter(prefix='/checkout', tags=['checkout'])

@router.post('/orders', response_model=schemas.OrderResponse, status_code=201)
async def place_order(
    request: schemas.PlaceOrderRequest,
    user = Depends(current_user),
    svc: service.CheckoutService = Depends(service.get_service),
):
    return await svc.place_order(user, request)
```

`main.py` mounts the per-feature routers:

```python
# main.py
from fastapi import FastAPI
from .checkout.router import router as checkout_router
from .identity.router import router as identity_router
from .products.router import router as products_router
from .shared.errors import register_exception_handlers

app = FastAPI(title='MyApp')
register_exception_handlers(app)

app.include_router(identity_router)
app.include_router(checkout_router)
app.include_router(products_router)
```

`main.py` reads as a manifest of features. It doesn't grow with the app's logic, only with the count of features.

---

## FA-002 — Pydantic schemas at the boundary

Pydantic schemas live in `schemas.py` and are the project's contract with the outside world. Input schemas validate incoming requests; output schemas (often `response_model=...`) shape responses.

```python
# checkout/schemas.py
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

class OrderItemInput(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)

class PlaceOrderRequest(BaseModel):
    items: list[OrderItemInput] = Field(min_length=1)
    shipping_address_id: UUID

class OrderResponse(BaseModel):
    # from_attributes lets model_validate() read a SQLAlchemy/SQLModel ORM
    # object's attributes (Pydantic v2). WITHOUT it, model_validate(orm_obj)
    # raises a ValidationError — see FA-003's `return OrderResponse.model_validate(order)`.
    # Any nested response schema built from ORM objects needs it too.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    total: int
    items: list[OrderItemInput]
```

**Framework-boundary carve-out (see `common/objects-and-data.md` OD-005).** Pydantic schemas are by design "hybrid" classes — they carry data shape *and* validation behavior. That's allowed; that's their job. Business rules still don't belong on them.

**Forbidden:** passing raw `dict` from a router into a service. The service signature is typed; the router validates, and only validated Pydantic models reach the service.

**Forbidden:** returning SQLAlchemy/SQLModel ORM objects directly from a router without a `response_model`. The ORM shape leaks relations, lazy loads, and DB column names. Always return a Pydantic response model (or set `response_model=` so FastAPI converts).

---

## FA-003 — Services orchestrate; repositories persist

Routers translate HTTP; services orchestrate; repositories talk to the database. The layers are short imports, not framework-imposed structure — discipline is the only enforcement.

```python
# checkout/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import CheckoutRepository
from .schemas import PlaceOrderRequest, OrderResponse
from ..identity.models import User

class CheckoutService:
    def __init__(self, repo: CheckoutRepository):
        self.repo = repo

    async def place_order(self, user: User, request: PlaceOrderRequest) -> OrderResponse:
        if not request.items:
            raise EmptyOrderError()
        order = await self.repo.create_order(user.id, request)
        return OrderResponse.model_validate(order)

# Dependency provider
def get_service(session: AsyncSession = Depends(get_session)) -> CheckoutService:
    return CheckoutService(repo=CheckoutRepository(session))
```

```python
# checkout/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Order

class CheckoutRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, user_id, request):
        order = Order(user_id=user_id, items=[...])
        self.session.add(order)
        await self.session.flush()
        return order
```

| Layer | Owns | Does NOT own |
|---|---|---|
| Router | HTTP, dependency wiring, response shape | Business rules, DB access |
| Service | Orchestration, business rules, calling repositories | HTTP details, raw SQL |
| Repository | Persistence per feature/aggregate | Business rules |

---

## FA-004 — Dependencies are the DI mechanism; use them deliberately

FastAPI's `Depends(...)` is the project's dependency-injection system. Use it for:

- **Per-request resources** — database sessions, transaction scopes, HTTP clients.
- **Authentication** — `current_user`, `require_admin`, etc.
- **Authorization** — feature-specific permission checks.
- **Service construction** — `get_service()` factories that compose a service with its repository and session.

```python
# shared/db.py
async def get_session() -> AsyncSession:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# identity/dependencies.py
async def current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    user_id = decode_token(token)
    return await get_user(session, user_id)
```

**Don't overuse dependencies for what's just a function call.** A dependency that takes no parameters and just returns a constant is overhead; just import it. `Depends` is for things that genuinely vary per request or need lifecycle management.

---

## FA-005 — Async everywhere, sync rarely (and deliberately)

FastAPI is async-first. Mixing sync and async path operations is allowed but rarely wise — sync handlers run in a threadpool, async handlers run on the event loop, and accidentally calling a blocking library from an async handler stalls the entire loop.

| Rule | Why |
|---|---|
| Path operation functions: `async def` by default | Event-loop friendly; matches the framework's strength |
| DB: use async drivers (`asyncpg`, `asyncmy`, `aiosqlite`) with `sqlalchemy[asyncio]` or SQLModel async | Avoid blocking the event loop |
| HTTP clients: use `httpx.AsyncClient`, not `requests` | Same |
| If you must call a sync blocking library, wrap with `await asyncio.to_thread(...)` or `fastapi.concurrency.run_in_threadpool` | Don't block the loop |

```python
# ❌ Bad — blocking call inside an async handler
@router.get('/things')
async def get_things():
    return requests.get('https://api/...').json()   # blocks the event loop

# ✅ Good — async HTTP client
@router.get('/things')
async def get_things(http: httpx.AsyncClient = Depends(get_http)):
    response = await http.get('https://api/...')
    return response.json()
```

This is `common/error-handling.md` EH-004 applied to FastAPI: never silently block on async code paths.

---

## FA-006 — Configuration via Pydantic Settings

Use `pydantic-settings` (or Pydantic v1's `BaseSettings`) to load environment variables once, with type validation, at startup:

```python
# shared/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    cors_origins: list[str] = []
    debug: bool = False

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False)

settings = Settings()
```

The app boots only if all required env vars are present. **Forbidden:** scattering `os.environ.get(...)` calls through feature code — that defers errors to the first request that hits the unset variable.

---

## FA-007 — Exception handling at the app boundary

Define a custom error hierarchy and register handlers with FastAPI:

```python
# shared/errors.py
class AppError(Exception):
    code: str = 'app_error'
    status_code: int = 400

class NotFoundError(AppError):
    code = 'not_found'
    status_code = 404

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={'error': {'code': exc.code, 'message': str(exc)}},
        )
```

Routers raise `NotFoundError(...)`; the handler returns the JSON. **No `raise HTTPException(404, ...)` inside services** — that's HTTP leaking out of the boundary. Services raise domain exceptions; the boundary translates.

This is `common/error-handling.md` EH-002 applied to FastAPI.

---

## FA-008 — Module-as-feature public surface

Each feature's `__init__.py` declares what other features may import:

```python
# checkout/__init__.py
from .router import router
from .service import CheckoutService
from .schemas import OrderResponse

__all__ = ['router', 'CheckoutService', 'OrderResponse']
```

Other features import `from ..checkout import CheckoutService` — never `from ..checkout.service import ...`. Same rule as `common/structure.md` ST-003.

Enforce with `import-linter`:

```toml
[importlinter:contract:feature-isolation]
type = forbidden
source_modules = ["myapp.checkout"]
forbidden_modules = ["myapp.identity.service", "myapp.products.repository"]
```

---

## FA-009 — Naming

| Type | Convention | Example |
|---|---|---|
| Feature folder | `snake_case`, plural | `checkout/`, `products/`, `orders/` |
| Pydantic schema | `PascalCase`, named by role | `PlaceOrderRequest`, `OrderResponse` |
| ORM model | `PascalCase`, singular | `Order`, `Product`, `User` |
| Service class | `PascalCase`, `<Feature>Service` | `CheckoutService` |
| Repository class | `PascalCase`, `<Feature>Repository` | `CheckoutRepository` |
| Dependency function | `snake_case`, descriptive | `current_user`, `get_session`, `get_service` |
| Exception class | `PascalCase`, ends in `Error` | `EmptyOrderError`, `NotFoundError` |
| Router variable | `router` (one per file) | `router = APIRouter(...)` |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Path operations with business logic and direct ORM access | Use a service |
| Returning ORM models directly without `response_model` | Leaks DB shape; specify `response_model=` |
| Sync DB / HTTP calls inside `async def` handlers | Blocks the event loop |
| `os.environ.get('X')` scattered through code | Use `Settings` at boot |
| `raise HTTPException(404, ...)` inside services | HTTP detail leaking into business layer; raise a domain exception |
| Cross-feature deep imports (`from ..billing.service import ...`) | Go through the feature's `__init__.py` |
| `shared/utils.py` or `shared/helpers.py` | Junk drawer |
| One giant `main.py` with every endpoint | Mount per-feature routers |
| Mixing async and sync in the same feature without reason | Pick one; cross-boundary `to_thread` only when needed |
| `BaseModel` schemas containing business workflows | Schemas validate; they don't orchestrate |

---

## Review checklist

```
Structure
  □ Top-level folders are features, not technical layers
  □ Each feature has router, service, schemas, repository (when DB-backed)
  □ main.py reads as a manifest of routers
  □ shared/ contains only code used by 3+ features

Boundary
  □ Every endpoint has a typed Pydantic request schema
  □ Every endpoint has response_model or returns a Pydantic instance
  □ ORM models never returned directly

Service layer
  □ Routers do not call repositories directly
  □ Services raise domain exceptions, not HTTPException
  □ Repositories never imported from routers

Async
  □ Path operations are async by default
  □ DB and HTTP clients are async-compatible
  □ Blocking sync calls wrapped with to_thread() when unavoidable

Configuration
  □ Env loaded once via Pydantic Settings
  □ App boots only if required config is present
  □ No os.environ.get scattered through feature code

Exception handling
  □ AppError hierarchy in shared/errors.py
  □ Centralized handlers registered on the FastAPI app
  □ No HTTPException raised from inside services
```
