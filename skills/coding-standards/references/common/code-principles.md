# Code Principles (SOLID, KISS, DRY)

Language-agnostic design principles for classes, modules, and systems — the canonical SOLID/KISS/DRY principles expected of any team that writes clean code.

Apply at the level of class/module/service design — one level above the function-internal rules in `functions.md`.

---

## DP-001 — Single Responsibility Principle (SRP)

> Every class, module, or service has exactly one reason to change.

A class serves an **actor** — a stakeholder whose needs drive change in that code. When a class serves two actors with two different concerns, a change for one will surprise the other.

**Smells:**
- A class with methods that fall into clearly different groups (e.g. `Employee` with `calculatePay`, `saveToDb`, `generateReport` — three actors: payroll, DBA, reporting).
- A class file is touched in commits for unrelated reasons across different sprints.
- The class has methods that some callers use and others don't — they're picking the slice that's "theirs."

**Apply:** when you identify two actors served by one class, split. Move each responsibility into its own class. The cost of an extra class is dwarfed by the cost of accidentally changing payroll logic while editing a report.

**Skip for:** trivial wrappers, plain data structures (DTOs, records, value objects). A `Money` value type doesn't need SRP — it has one job already.

---

## DP-002 — Open/Closed Principle (OCP)

> Software entities should be open for extension, closed for modification.

When you need to add a new variant of behavior, you should be able to do it by adding new code, not by editing existing working code.

**Apply when there's an actual recurring pattern of variation.** New payment provider, new report format, new shape type — these signal a polymorphism opportunity (see Objects & Data OD-002).

**Don't apply speculatively.** Designing for hypothetical future extensions you cannot name yet is over-engineering. Wait until the second variation appears, then refactor to abstract — that's when you actually know the shape of the variation.

**How:** extract an interface or abstract base for the varying piece; existing callers depend on the abstraction; new variants implement the abstraction without touching the old ones.

---

## DP-003 — Liskov Substitution Principle (LSP)

> A subtype must honor the full contract of its supertype.

If `S` is a subtype of `T`, then code written against `T` must continue to work when given an `S`. No surprises.

**Violations:**
- Subclass throws an exception the parent didn't declare (`Square extends Rectangle` and refuses non-equal width/height).
- Subclass weakens preconditions in a way callers don't expect.
- Subclass partially implements the interface and throws `NotSupported` from the rest.

**Apply only when inheritance is actually present.** This rule is about substitutability of subtypes — if you don't have inheritance hierarchies, you don't have LSP violations.

**Common fix:** if a subtype can't satisfy the parent's contract, the inheritance is wrong. Use composition instead — `Square` holds-a side length, doesn't extend Rectangle.

---

## DP-004 — Interface Segregation Principle (ISP)

> No code should be forced to depend on methods it does not use.

A fat interface that lumps together unrelated capabilities forces every implementer to handle methods it doesn't care about, and every consumer to depend on capabilities it doesn't call.

**Prefer many small focused interfaces** over one general-purpose one. A `Printer`, `Scanner`, and `Fax` shouldn't share an `OfficeDevice` interface that has all three sets of methods — that just forces every printer to no-op `scan()` and `fax()`.

**Apply when:** an interface has multiple methods AND multiple distinct consumers, where each consumer uses only a subset. Split the interface along consumer lines.

**Don't apply when:** a single interface really is consumed coherently by all callers. Splitting an interface no one wants split is just noise.

---

## DP-005 — Dependency Inversion Principle (DIP)

> High-level modules should not depend on low-level modules. Both should depend on abstractions.

Business logic (high level) should depend on an abstraction of its infrastructure (database, HTTP, file system, third-party SDK) — not on the concrete implementation. The concrete implementation depends on the same abstraction.

**Why it matters:**
- The infrastructure changes faster than the business logic. Tying business logic to today's choice (Postgres, Stripe v3, AWS SDK) means every infrastructure change forces business changes.
- Tests against an interface are cheap; tests against a real database/HTTP client are slow and flaky.

**Apply:**
- A use case / service / domain operation that uses a database or external service receives the dependency as an abstraction (interface, port, repository).
- Concrete implementations (database client, HTTP client) live in an outer layer that composes the dependency at the boundary.
- See per-framework architecture docs for how this maps in each stack.

**Skip for:** stable, same-layer imports. A utility class importing a stable language standard library does not need an abstraction — there's no rotation risk.

---

## DP-006 — KISS (Keep It Simple, Stupid)

> Choose the simplest design that satisfies the current, stated requirements.

Every layer of abstraction, every configuration option, every "what if" branch has a cost: more code, more decisions for the reader, more places to break. If removing the complexity would not break anything real, the complexity should not exist.

**Apply as the tiebreaker.** When two designs both satisfy the rules above, the simpler one wins. When in doubt about whether a pattern (Strategy, Visitor, Observer) is justified, omit it until the second case appears.

**Smells:**
- Configuration options no caller actually uses.
- A generic abstraction with only one concrete implementation.
- Pluggability for variations you cannot name.
- "We might need this later" — usually later never comes, and if it does, the shape isn't what you predicted.

**Trade-off honesty:** simpler is not always better. Sometimes a pattern *is* justified by current requirements (multiple payment providers, real polymorphism). KISS says don't *invent* complexity; it doesn't say strip out complexity you genuinely need.

---

## DP-007 — DRY (Don't Repeat Yourself)

> Every piece of knowledge has a single, unambiguous, authoritative representation within the system.

Already covered at the function level in `functions.md` (FN-011). Repeated here at the module/system level because the same principle applies up the stack:

- **Business rules** — a tax-calculation rule belongs in one place. Don't have it in the SQL view, the API serializer, and the UI display logic.
- **Type shapes** — a `User` type belongs in one place. Don't redefine it in the frontend and the backend; share or generate it.
- **Configuration** — a single source of truth for environment values. Not three `.env` files with slightly different copies.
- **Component structures** — if you find yourself copying a pattern (e.g. a list with empty state + loading + error), extract the pattern.

**Important caveat — the DRY paradox.** *Accidental* duplication (two things that look the same today but represent unrelated knowledge) is **not** a DRY violation. Forcing them into a shared abstraction will hurt when they diverge tomorrow.

**The test:** is the duplication about the *same piece of knowledge*, or just the same characters? Two screens both showing a price formatted to two decimals is shared knowledge (currency formatting). Two domain objects that both happen to have a `name: string` field are not.

---

## How these interact

When two rules pull in different directions, **DP-006 (KISS) is the tiebreaker.** A simpler design that mildly bends another principle beats a complex design that satisfies them all. The function-level and object-level rules in the other `common/` files already encode most of what SOLID demands; these principles are the macro-level statement of the same idea.
