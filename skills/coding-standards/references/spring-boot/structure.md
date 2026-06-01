# Spring Boot — Structure

## Builds on `common/structure.md`

This file adds only what's specific to Spring Boot (Java or Kotlin). The decomposition model —
business → feature → sub-feature → unit, one job per file, variants as one-interface-per-form, all the
ST rules — lives in `common/structure.md`, loaded alongside this. Read that for how to organize the
inside of any folder; this file is just the Spring specifics.

## Outer shell

Package by capability: each direct child package under the application's root package is one business
capability (`<capability>/`, `<other-capability>/`, …), holding its own controller, service, repository,
entities, and DTOs together. Component scanning and DI do the wiring — `@SpringBootApplication` picks up
annotated classes in the root package and its descendants, so no manual bean registration. Cross-cutting
code used by 3+ capabilities rises to a `shared/` package (this is `common/structure.md` ST-001/ST-004,
not restated here). Forbidden at the top: `controllers/`, `services/`, `repositories/`, `models/`,
`dtos/` — those are package-by-layer.

## Naming

- **Classes and files** — `PascalCase`, file name matches the class inside (`<Noun>Controller.java`,
  `<Noun>Service`, `<Noun>Repository`, `<Noun>` for an entity).
- **Package folders** — `lowercase`, named for the capability, never for a layer.
- **Roles read as `<Verb><Noun>`** where a name describes an action: request DTOs `<Verb><Noun>Request`,
  events `<Noun><PastVerb>Event`, behavior/factory methods on entities (`place`, `cancel`). Plain nouns
  for things (`<Noun>` entity, `<Noun>Response`).
- **Configuration / properties** — `<Scope>Configuration`, `<Scope>Properties`.

## Front door

A package has no `index` file. Its public surface is the **public types it exposes** — chiefly the Spring
beans (`@Service`, `@RestController`, a published interface) other packages inject. Callers depend on those,
not on a sibling's internal classes. For swappable variants, the **interface** is the front door and the
implementation is wired by component scan or a `@Configuration` bean.

## Spring specifics

- **Three-layer split inside each capability.** Controller (`@RestController`) does HTTP only:
  parse the request, call the service, shape the response. Service (`@Service`) owns the use cases:
  validates, coordinates repositories, raises events. Repository (`@Repository` / `JpaRepository`) does
  persistence. Forbidden: a controller calling a repository directly, or a service touching
  `HttpServletRequest`/`HttpServletResponse`. `@Transactional` belongs on the service, never the controller.

- **Entities own behavior tied to their own data** (`common/objects-and-data.md` OD-005 carve-out
  — JPA entities are intentionally hybrid). Put a method on the entity when it acts on that entity's own
  fields (`total()`, `cancel(reason)`); put it in a service when it coordinates several entities or external
  systems. Forbid Lombok `@Data` / `@Setter` on aggregates — they expose a public setter per field and break
  invariants. Use `@Getter` plus factory methods + behavior methods for mutation (Kotlin: `val` attributes,
  mutation through methods). One trap: if a response mapper reads `entity.getX()`, the entity must actually
  expose `getX()` — the field has to exist and `@Getter` (or an explicit accessor) has to cover it.

- **Map to response DTOs; never return an entity from a controller.** Entities carry lazy proxies,
  circular relations, and DB shape that leaks. Return a response DTO (a Java record is the natural fit) built
  by a `from(entity)` mapper. Request DTOs carry the Jakarta validation annotations; the controller takes
  `@Valid @RequestBody` so validation runs before the handler body.

- **One repository per aggregate, not a generic `Repository<T>`.** Extending
  `JpaRepository<T, ID>` for free CRUD is fine, but each capability's repository carries **domain-named
  query methods** callers actually use. Forbidden: a `BaseRepository<T>` every capability extends, exposing
  the same flat `findAll`/`save`/`delete` everywhere — that's the generic-name anti-pattern
  (`common/structure.md` ST-006). Keep complex queries (JPQL `@Query`, Specifications) on the repository.

- **Profiles and typed config.** Environment differences live in
  `application-{profile}.yml` (`dev` / `test` / `prod`), not in code. Bind config with
  `@ConfigurationProperties` to a typed object, validated at boot — a missing required property should make
  the app refuse to start. Forbidden: `System.getenv("X")` scattered through feature code.

- **Centralized errors via `@RestControllerAdvice`.** One global handler maps an app exception
  hierarchy to Problem Details (`ProblemDetail`, Boot 3). Services throw domain exceptions; the handler
  translates. Forbidden: `ResponseEntity.status(4xx)` shaped by hand across controllers
  (`common/error-handling.md` EH-002).

- **Cross-capability access via beans only.** Capability A reaches capability B through a Spring
  bean B exposes, never by importing B's internal classes. Broad reach-in is a design smell — the missing
  piece is usually a shared abstraction or an event between capabilities. Enforce with ArchUnit package
  rules.
