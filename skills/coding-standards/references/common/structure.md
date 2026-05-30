# Structure

Language-agnostic rules for how source files are organized into folders. Apply on top of any framework's `<framework>/structure.md`, which extends or carves exceptions to these rules.

A codebase's folder layout is its first piece of documentation. Done well, a new contributor opens `src/` and reads the business in 30 seconds. Done badly, every change touches five folders and nobody is sure where a new file belongs.

---

## ST-001 — Top-level folders inside `src/` (or the project root) name the business

Open the top of the source tree cold. The folder names should describe **what the product does**, not how it's built.

| ✅ Allowed at the top | ❌ Forbidden |
|---|---|
| `appointments/`, `prescriptions/`, `billing/`, `identity/` (capabilities) | `components/`, `hooks/`, `services/`, `repositories/`, `models/`, `controllers/`, `utils/` |
| The framework's required folders (`app/` for Next.js, `Http/` for Laravel) | Generic `types/`, `helpers/`, `common/` |
| `shared/` for genuinely cross-cutting code | Folder names that describe technical kind, not business meaning |

**Test:** show the top of `src/` to a teammate. Can they describe the product in one sentence using only the folder names? If they list framework concepts ("oh you have controllers and services and models"), the layout is wrong — that's package-by-layer, not package-by-business.

**Why this matters more than it looks:** when capabilities live as siblings at the top, deleting a feature deletes a folder, refactoring touches one folder, and a stranger finds the code by reading the business glossary. When layers live at the top, every change touches every layer.

**The named exception** is Laravel — Laravel's stock skeleton has top-level `Http/`, `Models/`, `Providers/` because the framework's conventions, generators, and ecosystem all depend on them. See `references/laravel/structure.md`. The rule there becomes: stock skeleton at the top of `app/`, capability subfolders *inside* each layer (`Http/Controllers/Orders/`, `Services/Orders/`).

---

## ST-002 — A folder is a module with one public entry

Each folder of substance has an `index` file (`index.ts`, `__init__.py`, `mod.rs`, `package-info.java`, `index.php` depending on the language) that lists what other code is allowed to use. Everything else is private.

```
checkout/
  Checkout.ts             ← internal
  cart.ts                 ← internal
  pricing.ts              ← internal
  index.ts                ← 🚪 declares the public surface
```

```ts
// ✅ Consumers go through the front door
import { Checkout } from './checkout'

// ❌ Consumers reach past the front door
import { Checkout } from './checkout/Checkout'
import { applyDiscount } from './checkout/pricing'
```

The same idea exists in every language:

| Language | Convention |
|---|---|
| TypeScript / JavaScript | `index.ts` re-exports the public symbols |
| Python | `__init__.py` lists `__all__` or imports public names from submodules |
| Rust | `mod.rs` (or `lib.rs`) declares which submodules are `pub` |
| Java | package boundaries + `public` access modifier on the entry types |
| C# | `public` types in the capability namespace are the surface; `internal` is hidden |
| Go | exported identifiers (capitalized names) form the package's API |
| PHP | namespace + public class visibility (Laravel's per-namespace convention) |

**Why this rule matters:** the public surface is a *contract*. Internals change without breaking callers; public symbols are committed to. Without an explicit entry, every file is implicitly public — and refactoring even a private helper becomes a breaking change because some distant caller imported it directly.

**Single-file folder exception:** if a folder has one file, callers may import the file directly. Add an `index` once the folder gains a second file.

---

## ST-003 — No deep imports past the folder's public API

This is the runtime enforcement of ST-002. Cross-folder imports must go through the destination folder's public entry. Reaching into another folder's internals breaks encapsulation, ties you to implementation details, and creates fanout chains that make refactoring impossible.

```ts
// ✅ Allowed
import { Checkout } from '@/checkout'

// ❌ Forbidden — bypasses the public API
import { applyDiscount } from '@/checkout/pricing'
import { Checkout } from '@/checkout/Checkout'
```

**Enforce it:**

- **JS / TS** — ESLint's `import/no-restricted-paths` or `eslint-plugin-boundaries`.
- **Python** — `import-linter` with layered/independence contracts, or a custom flake8 check.
- **Java / Kotlin** — ArchUnit rules.
- **C#** — Roslyn analyzers (`NetArchTest`, `ArchUnitNET`).
- **Go** — `go-cleanarch` or `import-boss`; alternatively use `internal/` folders (Go's built-in mechanism — code under `pkg/foo/internal/` is invisible to packages outside `pkg/foo/`).
- **PHP** — Deptrac.

A skill doesn't replace the linter. The skill catches the rule at write/review time; the linter catches it on every commit forever after.

---

## ST-004 — Rule of Three: nothing starts shared

Shared code is the most expensive code in the codebase — changing it means changing every caller, every test, every assumption that depends on it being stable. Earn shared status by demonstrating actual reuse.

The promotion path is mechanical:

1. **First use** → write the code inside the folder that needs it.
2. **Second use** → it is okay to **duplicate**. Yes, really. Two copies of a 5-line helper is better than a premature shared abstraction.
3. **Third use** → *now* extract to `shared/` (or the language's equivalent — `internal/` in Go, `common/` in some Python codebases).

**Why duplication at two is right:** when only two callers exist, you don't yet know whether they will diverge. A "shared" helper extracted from two callers gets a third user three weeks later who needs a slightly different version — and now you're stuck. Either you fork (and the third user reimplements it), or you parameterize (and the shared helper grows flags and conditionals until it's worse than the duplicates). At three users you actually know the shape.

**Anti-rule:** never *start* in `shared/`. Speculative shared code is the worst kind of shared code — written for users that may never exist.

---

## ST-005 — No junk-drawer files

A junk-drawer file is one whose name describes nothing about its contents: `utils.ts`, `helpers.ts`, `common.ts`, `misc.ts`, `lib.ts`, `Utils.cs`, `helpers.py`, `Util.java`. Everything ends up there because nothing has to.

**The smell:** a file that grows by accretion. Functions land in it because the author didn't think about where they actually belonged.

**The rule:** name files by **what they do**, not by **what kind of thing they are**.

| ❌ Junk drawer | ✅ Named |
|---|---|
| `utils.ts` | `format-currency.ts`, `parse-date.ts`, `slugify.ts` |
| `helpers.ts` | `validate-email.ts`, `compute-tax.ts` |
| `common.ts` | `http-client.ts`, `retry.ts`, `backoff.ts` |
| `misc.py` | `image_resize.py`, `text_normalize.py` |
| `Util.cs` | `MoneyFormatter.cs`, `DateRangeValidator.cs` |

`shared/lib/<purpose>.ts` is allowed because each file has a specific purpose. `shared/utils.ts` is forbidden because the name promises nothing.

**One-rule corollary — no junk-drawer constants/types files either.** A top-level `src/constants.ts` or `src/types.ts` is the same anti-pattern. Constants live next to the code that owns them; capability-wide types live in the capability's `types.ts`; truly app-wide types live in `shared/types/global.ts` with a narrow surface.

---

## ST-006 — Generic component or type names live only at the design-system layer

A name like `Card`, `Modal`, `Button`, `Selector`, `Repository<T>`, `BaseEntity` is too generic to mean anything about the business. Two `Card`s in the same project (an `AppointmentCard` and a `PrescriptionCard`) collide in autocomplete, in grep, and in the reader's head.

**The rule:**

- **Capability code** uses **domain-qualified** names: `AppointmentCard`, `ConfirmCancelDialog`, `PrescriptionDoseEditor`.
- **Design-system / shared UI** uses generic names: `Card`, `Modal`, `Button`, `Input`. These belong in `shared/ui/`, `components/ui/`, or whichever is the project's design-system folder — *never* inside a capability folder.

```
src/
  shared/ui/
    Card.tsx               ← generic primitive — design system
    Modal.tsx
  appointments/
    components/
      AppointmentCard.tsx  ← domain-qualified
      ConfirmCancelDialog.tsx
```

This isn't only about UI. The same principle applies to types:

- `Repository<T>` (one generic interface every capability implements) is a code smell — repositories should be capability-shaped (`OrderRepository`, `ProductRepository`) with domain methods.
- A `BaseEntity` parent class that every entity extends is suspect — usually a shared ID/timestamp shape is enough as a mixin, not as a parent.

---

## ST-007 — Tests, types, and styles live next to source

Anything that exists *because of* a file belongs *next to* that file.

```
checkout/
  Checkout.ts
  Checkout.test.ts        ← right next to the file under test
  cart.ts
  cart.test.ts
  types.ts                ← capability-local types
  index.ts
```

A separate top-level `tests/` mirror of `src/` (`tests/checkout/Checkout.test.ts`) is forbidden — tests drift away from the code they cover, get forgotten in refactors, and slow down navigation.

The same applies to `.types.ts`, `.styles.ts`, `.fixtures.ts`, `.stories.tsx`. Co-locate by default; promote to a shared folder only when the artifact is used by multiple files.

**Exception:** integration / end-to-end tests that exercise the whole app, not one file. Those legitimately live at the project root (`tests/e2e/`, `tests/integration/`) because they don't belong to any one source file.

---

## ST-008 — One file, one responsibility; grow folders by tier, not by accretion

Source is organized in four tiers: **Domain → Feature → Sub-feature → Unit**.

| Tier | Also called | What it is |
|---|---|---|
| Domain | Bounded Context, Capability | A top-level area of *what the product does* (ST-001) |
| Feature | Feature Module, Vertical Slice | A cohesive capability inside the domain |
| Sub-feature | Component, Concern | A distinct piece inside a feature (a folder once it earns 2+ files) |
| Unit | Module file | One responsibility, one file |

A *unit* (one file) has **one reason to change**. ST-005 governs a file's *name*;
ST-008 governs its *scope*. A file can have a perfect name and still be wrong — if
`payment.ts` parses input, talks to a gateway, and writes the ledger, it is three
units wearing one filename.

**The smell:** a well-named file that grows by accretion — it passes ST-005 (the
name is fine) but does several unrelated things.

**Detectable trigger — check before every write:**
- the file exceeds the project threshold (default ~400 lines / ~10 top-level
  declarations — tunable in `.coding-standards-structure`), **or**
- it holds 2+ unrelated responsibility clusters (e.g. a state machine *and* regex
  parsers *and* file I/O), **or**
- you are about to *add* a concern to a file that already owns a different one.

**Then:** extract the new concern into a named sibling unit. When three siblings
share a theme, promote them to a sub-feature folder with its own `index` (Rule of
Three, ST-004). **Never create a folder for a single file**, and if a feature has a
handful of flat units, stop at the feature tier — a sub-feature folder there is
over-engineering (DP-006 KISS).

**Worked example — a unit doing three things splits into siblings:**

```
# Before — one unit, three responsibilities
billing/
  invoice.ts        ← parses requests + computes totals + persists rows
  index.ts

# After — one responsibility per unit, same public door
billing/
  parse-invoice-request.ts   ← input parsing
  invoice.ts                 ← the orchestrator (compute + coordinate)
  invoice-store.ts           ← persistence
  index.ts                   ← still the only public entry (ST-002)
```

The behavioral companion is **DP-002** (extract an abstraction when you have 2+
variants of a behavior) — structure splits *responsibilities*; DP-002 splits
*variants*.

> **Enforcement note:** the `warn-god-file.py` hook emits an *advisory* warning at
> write time when a file crosses the threshold (it never blocks — a raw size count
> has too high a false-positive rate to gate on). The judgement parts of this rule
> (responsibility clusters) are checked by Worker 1 and in Review mode.

---

## How framework files extend this

Every `references/<framework>/structure.md` builds on these rules. A framework file may:

- **Specialize a rule** — e.g., Next.js says "`app/` is thin, business logic lives in capabilities" (specialization of ST-001).
- **Add framework-specific rules** — e.g., Cocos Creator's "bundles don't nest," NestJS's "one feature, one module file."
- **Carve a named exception** — e.g., Laravel keeps the stock skeleton at the top (ST-001 exception), NestJS DTOs are intentionally "hybrid" (Objects & Data OD-004 exception).

A framework file may **not** silently override these rules. If a framework's idiom genuinely conflicts with a structural rule, the framework file names the conflict explicitly and explains why the carve-out is necessary.

---

## Review checklist (universal — apply to every file in every project)

```
Top-level layout
  □ Folders at the top of src/ describe the business, not technical layers
  □ No utils.ts, helpers.ts, common.ts, misc.ts, lib.ts, etc.
  □ No top-level mega-files (src/types.ts, src/constants.ts)
  □ shared/ contains only code with 3+ real users

Per folder
  □ Has an index entry (index.ts, __init__.py, mod.rs, ...) once it has 2+ files
  □ Generic names (Card, Modal, Repository<T>) only in the design-system / shared layer
  □ Capability code uses domain-qualified names

File scope (ST-008)
  □ No unit holds 2+ unrelated responsibilities (god-file)
  □ Oversized files (advisory warn-god-file threshold) are split into named siblings
  □ Sub-feature folders are earned (2+ cohesive files), not created for symmetry

Imports
  □ Cross-folder imports go through the folder's public entry
  □ No deep imports past index / public API
  □ Enforced by linter (ESLint, import-linter, ArchUnit, ...)

Co-location
  □ Tests next to source, not in a parallel tests/ tree
  □ Types, fixtures, stories next to the files they describe
```
