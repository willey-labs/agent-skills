# Node.js (Express / Fastify) — Structure

## Builds on `common/structure.md`

This file adds only what's specific to plain Node backends on Express or Fastify (not NestJS). The
decomposition model — business → feature → sub-feature → unit, one job per file, front doors, Rule of
Three, no junk drawers — lives in `common/structure.md`, loaded alongside this. Read that first; below is
just the Node specifics.

## Outer shell

Express and Fastify impose no layout. Nothing scaffolds `app/` or `Controllers/` for you — the folder
names are entirely yours, so put business folders at the top of `src/` and decompose inside them per
`common/structure.md`. Two files do sit at the root: a bootstrap file that builds the app and listens, and
a composition file that mounts every feature's router plus shared middleware.

Because no framework enforces the shape, discipline is the only thing holding it together. The trap is a
top-level `routes/` (or `services/`, `repositories/`) folder that collects every feature's like-typed
files — that spreads one feature across four folders and is package-by-layer. Keep each feature's route,
service, repository, schema, and types together in its one folder.

## Naming

- **Files** — `kebab-case`, named by the job: `<verb>-<noun>.ts` for logic, server calls, and schemas.
- **Types, classes, error classes** — `PascalCase`.
- **Exported router** — `camelCase` + `Router` suffix (`<feature>Router`); **exported service** —
  `camelCase` (`<feature>Service`).
- **Co-located** — `<name>.test.ts`, `<name>.types.ts`, beside what they describe.

## Front door

A folder's public API is its `index.ts`. A feature re-exports only what the composition file and other
features need to wire it up — typically its router, and any middleware or service that others call. The
service, repository, schemas, and internal types stay private. Other folders import through the front door
(`@/<feature>`) and never reach past it into a sibling file (`common/structure.md`, ST-002/003). The
composition file is the one place every feature's router is mounted.

- **A nested feature must build on its parent (ST-009).** A child folder nested inside a parent feature
  is a true sub-feature only if it imports from the parent's front door and is part of it. One that
  ships its own store + service + routes and shares only a helper type is a **peer misfiled as a
  child** — give it its own top-level feature folder.

## Express / Fastify specifics

- **Routes are thin; services own the use cases.** A route maps the HTTP path to a handler that
  validates input and delegates to a service — no business rules, no calculations, no DB access in the
  route. If a handler runs past a few lines, the body belongs in a service.

- **Services orchestrate; repositories persist.** No DI container — just imports. The service
  validates, calls the repository, raises events; it never writes raw SQL or ORM calls. The repository
  persists per aggregate (not per table) and holds no business rules. A route calling the database
  directly means both layers are missing.

- **Validate at the boundary.** Express and Fastify give you no validation. Define a schema in
  `<feature>.schema.ts` with a validator of your choice, infer (or declare) the TypeScript type from it so
  route, service, and repository agree on the shape, and validate **before** calling the service. No
  service method ever accepts raw `req.body` or `unknown`.

- **One centralized error handler + structured error classes.** Each error is a `PascalCase`
  class carrying a stable code and HTTP status (a base `AppError`, plus variants like `ValidationError`,
  `NotFoundError`). Handlers `throw` these; they never scatter `res.status(400).send(...)` through route
  bodies. One error-handling middleware, registered **last**, translates a known error to its status and
  turns anything unrecognized into a logged 500.

- **Async/await with a single error path.** Every handler is `async`; old callback style is out.
  Thrown errors must reach the central handler with nothing swallowed. **Express 5** routes thrown async
  errors to the error handler automatically; **Express 4** does not — wrap each handler in `try/catch` that
  calls `next(err)`, or use an `asyncHandler` helper. **Fastify** handles async routes natively: return a
  value or throw, and the framework routes it.
