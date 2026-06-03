# Objects & Data

Language-agnostic rules for class, object, and data-structure design. Applies wherever a language has the concept of an object with private state or a struct/record with public fields.

---

## OD-001 — Expose behavior, not data

Most developers make fields private and then immediately add a getter and setter for every one of them — which makes the data effectively public again.

The reason to keep fields private is the freedom to change *how* they are stored without breaking callers. Getters and setters give that freedom back to no one — the moment you expose the shape, you've committed to it.

**The principle:** abstraction is not about wrapping fields in functions. It's about exposing what users can *do* with the data, not how the data is stored.

**Two storage representations of the same point:**

```
class CartesianPoint { x: number; y: number; }
class PolarPoint     { r: number; theta: number; }
```

Both expose their internals. Neither hides anything. A better abstraction:

```
interface Point {
  getX(): number;          // works regardless of storage
  getY(): number;
  getR(): number;
  getTheta(): number;
  setCartesian(x: number, y: number): void;
  setPolar(r: number, theta: number): void;
}
```

The caller manipulates the point without knowing whether it's stored as `(x, y)` or `(r, θ)`. The interface can also enforce policy — read coordinates independently, but require setting them as an atomic operation. Public fields cannot enforce that.

**Vehicle example:**

```
// Still exposes structure — fields hidden, but methods describe fields
getFuelTankCapacityInGallons(): number
getGallonsOfGasoline(): number

// Exposes behavior — implementation genuinely gone
percentFuelRemaining(): number
```

The second form hides whether fuel is in gallons, liters, kilowatt-hours, or kilojoules. None of that matters at the call site.

**How to apply:** before adding a getter, ask *what does the caller actually do with this value?* If the answer is "compute something derived from it," put that computation behind a method on the object, not at the call site.

---

## OD-002 — Choose objects vs data structures by the direction of change

Every class is a bet on what kind of change comes next. The two extremes have opposite tradeoffs.

Some types come in variants — a set of named kinds, each with its own behavior. There are two ways to model them, and the choice is about where the next change lands.

**Behavior in the type** — one class or module per variant, each owning its own logic. Adding a variant is one new unit; nothing else moves. Adding an operation touches every variant.

**Data plus central functions** — variants are plain data; functions elsewhere `switch` on a tag to decide what to do. Adding an operation is one new function; adding a variant means editing every function that switches.

Pick the form that makes the *expected* change the small one. Variants keep arriving over time → behavior in the type. The set is fixed and new operations keep arriving → data plus functions.

**If the task already names the variants and each carries its own behavior, put the behavior in the type.** That is modeling what you were given, not a speculative abstraction — don't talk yourself out of it with "keep it simple."

**Data plus a tag is the narrow case, not the default.** Use it only when the variants are near-pure data, the set is closed, and the matching happens in one or two places. Even then, every `switch` must be exhaustive — a missing variant must fail to compile. An `if/else` chain, or a `default` that returns a fallback, silently mishandles a new variant; that is a defect. Once three or more places switch on the same tag, the behavior is scattered — move it into the type.

---

## OD-003 — Law of Demeter: talk to friends, not strangers

A method may only call methods on:
- the object it belongs to (`this`)
- objects it creates
- objects passed as arguments
- objects it holds as fields

It should **not** call methods on objects returned by those calls. Chains like `context.getOptions().getScratchDirectory().getAbsolutePath()` reach through three strangers — that's a lot of structural knowledge for one line.

**Important caveat:** Demeter only applies to **real objects** (things that hide data and expose behavior). It does **not** apply to **data structures** (things designed to expose internals — DTOs, records, plain old data). Walking the fields of a data structure is fine, that's what they're for.

So the question for a chain is: *is each link a real object or a data structure?* Real objects → chain violates Demeter. Data structures → no violation.

**Naive fix that doesn't work:** collapse the chain into one method name that encodes the path (`context.getScratchDirectoryAbsolutePath()`). The structural knowledge didn't disappear — it just moved into the method name. You now need a new method for every combination.

**Real fix — ask why you need the value.** If the caller actually wants to *create a scratch file*, tell the object that:

```
context.createScratchFile(name);
```

The chain collapses. The caller knows nothing about scratch directories or absolute paths. The structure stays behind the boundary where it belongs.

---

## OD-004 — Don't build hybrid classes

A hybrid class exposes data through getters/setters **and** does real work via methods. It's the worst of both worlds:

- The data leaked through getters — callers depend on the shape, so you can't change storage.
- The behavior is trapped inside — when a new variant arrives (e.g. subscription pricing), the discount logic can't be reused without dragging the whole class.

Adding a new operation is hard (must touch the class), and adding a new type is hard (the data shape is already public). Both axes locked.

**Commit to one identity:**

- **Pure data structure** — public fields, no behavior. DTOs carrying data between layers. Database row records. Their job is to be inspected; do that, nothing more.
- **Active Record** — a data structure with **navigational** methods (`save`, `delete`, `reload`) that map to database rows. That's still a data structure — `save` is not business logic, it's just persistence. **The bug is adding business logic** (`calculateDiscount`, `applyPromotion`) on top.
- **Pure object** — hides data, exposes behavior. Business rules live here.

**The fix for a hybrid:** don't strip `save`/`delete` from your Active Record. Move the *business rules* (pricing, eligibility, validation) out into separate objects. The Active Record stays a clean data carrier; the business object owns the logic.

**How to spot a hybrid:** the class has both `getX()/setX()` for most of its fields *and* methods that perform calculations or enforce rules. Split it — pricing logic into its own object, persistence stays in the record.

---

## OD-005 — Frameworks demand "hybrid" shapes at their boundary; that's allowed

A real conflict you will hit in review: every web framework's idiomatic patterns produce classes that look like the "hybrids" OD-001 and OD-004 forbid.

| Framework | The "hybrid" shape | Why it exists |
|---|---|---|
| **NestJS** | DTOs with `@IsEmail()`, `@Min(0)`, custom validators | The framework reads decorators on the class to validate the wire shape |
| **Laravel** | Form Requests with `rules()` + `authorize()` methods on the request class | Same — request validation is part of the framework contract |
| **NestJS / Laravel / Spring / EF Core** | Entities with persistence decorators (`@Entity`, `@Column`, `@Id`, `[Key]`) | The ORM reads the decorators to map to the database |
| **Cocos Creator** | Components with `@property`-decorated fields exposed to the editor | The editor reads decorators to render the inspector |
| **Spring** | Controllers with `@RestController`, request DTOs with `@RequestBody` + Jakarta validation | Same — Spring reads the annotations to bind |
| **Django / FastAPI** | Pydantic models / Django models with validation methods | The framework's input/output contract |

These look like hybrids because they expose data shape *and* attach behavior (validation, persistence, editor display) to the class. **They are not the smell OD-004 is about.** OD-004 warns against classes where *business rules* mix with data getters/setters — pricing logic on an Order entity that also exposes raw fields. The framework-boundary classes above don't do that: their "behavior" is *infrastructure* (validation, persistence, editor binding), not business rules.

**The rule:**

1. **Framework-boundary classes** (DTOs, Form Requests, EF/TypeORM/JPA entities, Pydantic models, Cocos components) are *allowed* to look like hybrids. They exist to bridge a framework contract; that's the framework's design.
2. **Business rules still don't live on those classes.** An Order entity may carry `@Entity` decorators and `IsCancellable()` (about its own data). It must not carry `ChargeCustomer()` or `SendOrderConfirmation()` — those are orchestration, and they belong in services or domain objects.
3. **The framework boundary is a *thin* layer.** When the boundary class starts to grow business methods, you've crossed the line — extract them out.

**How to spot the real OD-004 violation inside a framework-boundary class:** business logic that goes beyond *what does this thing do with its own data?* If the method talks to other services, dispatches events, or coordinates across aggregates, it doesn't belong on the boundary class — push it into a service.

Each framework's structure file (`nestjs/`, `laravel/`, `csharp/`, `cocos-creator/`, `spring-boot/`, …) carves the carve-out concretely for that stack.
