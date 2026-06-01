# FastAPI — Structure

## Builds on `common/structure.md`

This file adds only what's specific to FastAPI. The decomposition model — business → feature →
sub-feature → unit, one job per file, front doors, the ST rules — lives in `common/structure.md`, loaded
alongside this. Read that first; this file is just the FastAPI specifics.

## Outer shell

FastAPI imposes no layout of its own — it scaffolds nothing and forces no top folders. So the universal
model applies at full height: name the top-level folders by business feature and decompose inside them per
`common/structure.md`. Discipline is the only thing holding the shape together; there is no framework
convention to lean on, so the ST rules are the whole enforcement.

For a very small app, a feature may start as a single file holding its router, service, and schemas
together; split it into a folder once it grows past one job per file.

## Naming

- **Files and modules** — `snake_case.py`, named by the job they do (`<verb>_<noun>.py`), never by kind.
- **Classes** — `PascalCase`: ORM models are singular nouns (`<Entity>`), services and repositories carry the
  feature name (`<Feature>Service`, `<Feature>Repository`), schemas are named by role
  (`<Verb><Entity>Request`, `<Entity>Response`), exception classes end in `Error`.
- **Dependency functions** — `snake_case`, descriptive (`current_user`, `get_session`).
- **Generic names** belong only in the shared layer (`common/structure.md`, ST-006).

## Front door

A feature is a package; its front door is its `__init__.py`, which re-exports the public names and sets
`__all__`. Other features import through it (`from ..<feature> import <Name>`) and never reach into a
sibling's internals (`common/structure.md`, ST-002/003). Enforce it with `import-linter`.

## FastAPI specifics

- **One `APIRouter` per feature.** Each feature defines a single `router = APIRouter(...)` in its
  router module. `main.py` mounts the per-feature routers and nothing else, so it reads as a manifest of
  features and grows only with their count, not with logic.

- **Pydantic schemas at the boundary.** The router validates incoming requests into typed schemas
  and never passes a raw `dict` into a service; only validated models cross the line. Set `response_model=`
  (or return a response schema) so an ORM object never leaks out directly with its relations and column
  names. A response schema built from an ORM object needs `model_config = ConfigDict(from_attributes=True)`
  — including every nested response schema. Never reuse an input schema as a nested response type; input and
  output are separate shapes.

- **`Depends(...)` is the dependency-injection mechanism.** Use it for things that genuinely vary
  per request or need lifecycle management: per-request resources (DB sessions, HTTP clients),
  authentication and authorization, and service-construction factories. A dependency that takes no
  parameters and just returns a constant is overhead — import it instead.

- **Async handlers by default (a concurrency rule, not error handling).** A blocking or sync call
  inside an `async` handler stalls the whole event loop and freezes every other in-flight request. Use
  async drivers and async HTTP clients; when a sync library is unavoidable, push it off the loop with
  `asyncio.to_thread(...)` or `run_in_threadpool`.

- **Configuration via Pydantic Settings.** Load environment variables once at startup through a
  `BaseSettings` class with typed fields, so the app boots only when required config is present. Don't
  scatter `os.environ.get(...)` through feature code — that defers the failure to the first request that
  hits the unset variable.

- **One exception handler at the app boundary.** Services raise domain exceptions (an `AppError`
  hierarchy with a status code and a code); a handler registered on the app translates them into responses.
  Never `raise HTTPException(...)` inside a service — that leaks HTTP into the business layer. This is
  `common/error-handling.md` EH-002 applied to FastAPI.
