# NestJS — Structure

## Builds on `common/structure.md`

This file adds only what's specific to NestJS. The decomposition model — business → feature →
sub-feature → unit, one job per file, front doors, Rule of Three, no junk drawers — lives in
`common/structure.md`, loaded alongside this. Read that first; the rules below are the Nest-specific bits.

## Outer shell

NestJS is module-per-feature: one folder = one module = one feature. The top folders under `src/` are
yours to name, so business folders go straight at the top (`src/<business>/<feature>/`), each owning its
own `*.module.ts`. The only fixed entries are `main.ts` (bootstrap) and `app.module.ts` (composition
root). Don't carve out top-level `controllers/`, `services/`, or `repositories/` — that spreads one
feature across six folders. Cross-cutting infrastructure used by 3+ features lives in `shared/`
(`common/structure.md`, ST-004).

## Naming

Inside a feature, files use **kebab-case with Nest's layer suffix**; the class inside is **PascalCase**.

- `<feature>.module.ts` → `class <Feature>Module`
- `<feature>.service.ts` → `class <Feature>Service`
- `<feature>.controller.ts` → `class <Feature>Controller`
- `<verb>-<noun>.dto.ts` → `class <Verb><Noun>Dto`
- `<noun>.entity.ts` → `class <Noun>`
- Same-kind plurals get a folder once 3 earn it (`dto/`, `entities/`, `guards/`, `strategies/`); a lone
  one stays a single file beside its module (`common/structure.md`, ST-004).
- Generic names (`Card`, `Repository<T>`, `BaseEntity`) only in `shared/`, never inside a feature
  (`common/structure.md`, ST-006).

## Front door

A feature's public surface is gated **twice and they must agree**:

- `index.ts` re-exports what other features may import (the import-time surface).
- the module's `exports: []` array lists what can be injected elsewhere (the runtime surface).

If a provider isn't in `exports`, it can't be injected, so it has no business in `index.ts` either. Other
features import through `index.ts` and never reach past it (`common/structure.md`, ST-002/003).

## NestJS specifics

- **Each layer is its own file with the matching suffix**. Controller, service, and entity are
  separate files, not one `<feature>.ts` doing all three — the suffix *is* the one-job-per-file boundary.

- **HTTP in controllers, orchestration in services, domain on entities**. A controller binds the
  route, validates the DTO, returns a status — no DB calls, no business rules. A service coordinates
  repositories and pre-conditions — no raw queries, no HTTP details. An entity owns its own invariants and
  behavior (`<entity>.cancel()`). A controller calling `repo.findOne()` / `repo.save()` directly means the
  service layer is missing; a service full of `if/else` over a behavior-less entity means logic belongs on
  the entity instead.

- **DTOs at the controller boundary; entities stay inside**. The DTO is the wire shape (validated
  with `class-validator`); the entity is the domain shape. They are not interchangeable. Never return an
  entity straight from a controller — it leaks internal and persistence shape; map to a response DTO at the
  boundary.

- **DTOs and ORM entities are the allowed hybrid** (`common/objects-and-data.md`, OD-005). Their
  validation/persistence decorators are framework-required behavior, not the data-plus-logic anti-pattern.
  The line stays firm: business rules (charging, dispatching events, crossing aggregates) belong in
  services or domain objects, never on a DTO or entity.

- **No repository wrapping a single ORM model.** Repositories are domain-shaped per feature/aggregate, not
  a `find`/`save`/`delete` shell per table — the ORM already is that layer.
