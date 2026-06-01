# C# / .NET — Structure

## Builds on `common/structure.md`

This file adds only the C#/.NET specifics. The decomposition model — business → feature →
sub-feature → unit, one job per file, the front door, Rule of Three, all the ST rules — lives in
`common/structure.md`, loaded alongside this. Read that for how to organize the inside of any folder.

## Outer shell

Business folders go at the top of the **one application project** — `.NET` doesn't force a layout, so
they're yours to name. Each folder is a business capability and owns everything that capability needs;
adding or removing a capability touches one folder. This is vertical-slice style: there is **no
`Features/` wrapper** — the top-level folders inside the project already are the features.

```
<Capability>/                ← a business capability, flat at the project top
  <Resource>Endpoints.cs     ← or <Resource>Controller.cs
  <Resource>Service.cs
  <Resource>Repository.cs
  <Resource>.cs              ← entity
  <Verb><Resource>Request.cs ← input DTO
  <Resource>Response.cs      ← output DTO
```

Forbidden at the top of the project: kind-named folders (`Controllers/`, `Services/`, `Repositories/`,
`Models/`, `Dtos/`) and the layered-DDD wrappers (`Domain/`, `Application/`, `Infrastructure/`). Those
spread one capability across many folders — the thing we organize against.

## Naming

- **Folders are namespaces → `PascalCase`** (`<Capability>/`, plural). The folder name is part of the
  namespace: `<Capability>/<Resource>Service.cs` is `<Root>.<Capability>.<Resource>Service`. Never
  lowercase a folder.
- **Files → `PascalCase.cs`** matching the type inside.
- Entities are singular nouns (`<Resource>.cs`); services `<Resource>Service`; repositories
  `<Resource>Repository`; input DTOs `<Verb><Resource>Request`; output DTOs `<Resource>Response`;
  events past-tense (`<Resource><PastVerb>`); exceptions `<Specific>Exception`; async methods end
  `Async`; interfaces keep the `I` prefix (`I<Name>`) — it's the C# convention.

## Front door

A capability's public surface is its **public service / endpoint class** — callers depend on those, not
on its siblings. Hide everything else with `internal`; cross-capability code talks through the public
service (or a domain event), never reaches into another capability's internals.

## C#/.NET specifics

- **Each capability owns every layer.** Endpoints, service, repository, entities, DTOs, events,
  and exceptions all live in the capability folder. When one kind grows past a handful (10 endpoints, 8
  events), give it a sub-folder *inside the capability* (`<Capability>/Events/`) — only once earned. A
  repository is optional: add it when queries don't belong on the entity or when an abstraction helps
  testing; don't wrap a single entity in a `find`/`save` repository that adds nothing.
  - **Optional one-file-per-use-case (pure vertical slice):** instead of grouping by file kind, give each
    use case one file holding its command record, handler, validator, and endpoint mapping together
    (`<Capability>/<VerbResource>.cs`), with the shared entity and repository beside them. Adding a use
    case is then literally one new file. Pick one style per project; don't mix within a capability.

- **Behavior placement.** Put behavior *on* the entity when it acts on the entity's own data
  (state transitions, totals); use private setters and factory methods so callers can't bypass
  invariants. Put it in a **service** when it orchestrates across capabilities or external systems. A
  method must use the parameters it takes — if it ignores them, it's on the wrong type. (EF entities with
  persistence attributes and request DTOs with validation attributes are the framework-sanctioned hybrid;
  see `common/objects-and-data.md` OD-005.)

- **Wire DTOs separate from entities.** Never return an EF entity from an endpoint — entities
  carry navigation properties, circular references, and DB-shaped detail that leaks. Map to a response
  DTO (`record`) via a static `From(entity)` factory. Validate input DTOs at the boundary; never trust
  the wire shape inside a service.

- **Async / cancellation / nullability hygiene.** Enable nullable reference types
  (`<Nullable>enable</Nullable>`). Async/await end-to-end with a `CancellationToken` as the last
  parameter of every async method crossing a layer. Never `.Result`, `.Wait()`, or
  `.GetAwaiter().GetResult()` — they deadlock and starve the thread pool. `async void` only for event
  handlers. `sealed` by default.

- **Wrap primitives when a type-mix would silently compile.** A `Guid` could be one entity's id or another's;
  passing one where the other is expected compiles fine and ships a bug. Wrap such ids/quantities
  in a value object (`readonly record struct`) when the type travels far enough to be mixed up, carries
  invariants, or drives behavior. Don't wrap one-off internal ids that never cross a boundary — that's
  over-engineering.

- **DI registrations owned by the capability.** Each capability exposes an `Add<Capability>()`
  extension that registers its own services, and a `Map<Resource>Endpoints()` that registers its own
  endpoint group. `Program.cs` just chains them, reading as a manifest of capabilities — not a growing
  block of registration soup.

**Multi-project DDD** (`<Cap>.Domain` / `.Application` / `.Infrastructure` / `.Api`) is **not** the
default — it makes every feature touch several projects. Adopt it only when compile-time enforcement of
layer boundaries is genuinely needed, or the domain is complex enough (regulatory, financial) to warrant
bounded contexts. The flat-capability shape is the starting point; promotion is mechanical when it comes.
