# Vanilla JS / TS — Architecture

The chosen pattern for plain JavaScript or TypeScript projects without a framework (Node scripts, browser-only apps, libraries, CLIs): **folder-as-module + co-location**.

The vanilla stack has no opinion of its own — these two principles supply the structure.

---

## The philosophy in one sentence

> A folder is a module with a defined public API. Everything inside that folder lives next to what uses it. Things move up the tree only when proven shared.

---

## Builds on `common/structure.md`

This file is the closest of all the framework files to the universal structural rules in `references/common/structure.md`, because vanilla JS/TS has no framework on top to constrain folder layout — the structural rules *are* the architecture. Read `common/structure.md` first; the rules below add specifics like the per-folder barrel, the no-mega-root-barrel rule for tree-shaking, and the default naming table.

---

## Mandatory shape (browser/Node app)

```
src/
  main.ts                          ← entry point (browser bootstrap or CLI start)

  checkout/                        ← FEATURE folder (folder-as-module)
    Checkout.ts                    ← public interface implementation
    cart.ts                        ← internal
    pricing.ts                     ← internal
    format-card-number.ts          ← internal helper
    checkout.test.ts               ← test co-located with source
    types.ts                       ← feature-local types
    index.ts                       ← 🚪 public API (only exports visible elsewhere)

  auth/
    Auth.ts
    token.ts
    auth.test.ts
    types.ts
    index.ts

  shared/                          ← used by 3+ features (Rule of Three)
    dom/
      query.ts
      events.ts
      index.ts
    lib/
      date.ts
      currency.ts
      http.ts
      index.ts
    types/
      global.ts                    ← only truly app-wide types
```

For a **library** package (consumed by other code, no app entry), `src/main.ts` becomes `src/index.ts` and the top-level folders are the library's public modules.

---

## VJS-001 — Each folder is an importable module via `index.ts`

A folder is treated as one unit. Consumers import from the folder path; the folder's `index.ts` declares what's public.

```ts
// src/checkout/index.ts — the public API of the checkout folder
export { Checkout } from './Checkout'
export type { CheckoutResult, PaymentMethod } from './types'
// cart.ts, pricing.ts, format-card-number.ts stay private
```

```ts
// ✅ Allowed
import { Checkout } from './checkout'

// ❌ Forbidden — deep import past the public API
import { Checkout } from './checkout/Checkout'
import { formatCardNumber } from './checkout/format-card-number'
```

This is the **brick** every other rule builds on.

---

## VJS-002 — Co-locate: things that change together live together

A helper used by only one component lives in that file. A helper used by multiple files in one feature lives in that feature folder. A helper used across 3+ features moves to `shared/`.

| Used by | Lives in |
|---|---|
| One file | The same file (or right next to it) |
| One feature | That feature's folder |
| 3+ features | `shared/` |

```ts
// ✅ Inside the file — only this component uses formatCardNumber
function formatCardNumber(value: string): string {
  return value.replace(/(\d{4})/g, '$1 ').trim()
}

export function renderCheckoutForm() {
  // ...uses formatCardNumber
}
```

No `utils/format-card-number.ts` until a second user appears.

---

## VJS-003 — Tests, types, styles live next to source

```
checkout/
  Checkout.ts
  Checkout.test.ts          ← right next to the file under test
  types.ts                  ← feature-local types
  cart.ts
  cart.test.ts
  index.ts
```

A separate top-level `tests/` mirror of `src/` (`tests/checkout/Checkout.test.ts`) is forbidden — tests drift away from the code they cover.

Same for `.types.ts`, `.styles.ts` (when present), `.fixtures.ts`. Anything that exists *because of* a file belongs *next to* that file.

---

## VJS-004 — No global mega-files

These are the junk-drawer anti-patterns this design exists to prevent:

| Forbidden | Why |
|---|---|
| `src/utils.ts` / `src/helpers.ts` | Junk drawer — accumulates unrelated functions |
| `src/types.ts` (top-level mega-file) | Types belong next to their owners |
| `src/constants.ts` (top-level mega-file) | Constants belong next to their owners |
| `src/lib/utils.ts` | Same junk drawer, one level deeper |

**Allowed:** `shared/lib/<purpose>.ts` with a specific, named purpose (`date.ts`, `currency.ts`, `http.ts`). The rule is *named files, never `utils`*.

---

## VJS-005 — Promote with the Rule of Three

To prevent both over-sharing (`shared/` becomes the new junk drawer) and under-sharing (every feature reimplements the same helper):

1. **First use** → write it inside the file.
2. **Second use** → it's okay to duplicate. *Yes, really.* Two copies of a 5-line helper is better than a premature abstraction.
3. **Third use** → *now* extract to `shared/`. By the third use, you actually know the shape.

**Why duplication at two:** when two callers exist, you don't yet know whether they'll diverge. Forcing them into a shared abstraction too early creates a maintenance trap when one of them needs a slightly different version next month.

---

## VJS-006 — No deep imports past `index.ts`

Imports across folder boundaries must go through the folder's `index.ts`. Internal files of a folder are private.

```ts
// ✅ Allowed
import { Checkout } from './checkout'
import { formatCurrency } from './shared/lib/currency'

// ❌ Forbidden — bypasses the public API
import { Checkout } from './checkout/Checkout'

// ❌ Forbidden — reaching into another feature's internals
import { tokenize } from './auth/token'   // should be exported from auth/index.ts if needed
```

Enforce with ESLint's `import/no-restricted-paths` rule (or the equivalent for your linter).

**Single-file folders are an exception:** if a folder only has one file, you can import the file directly. Add an `index.ts` once it gains a second file.

---

## VJS-007 — Avoid mega-barrels at the root

A single `src/index.ts` that re-exports the entire app kills tree-shaking. Bundlers can't statically prune what they can't see.

```ts
// ❌ Bad — kills tree-shaking
// src/index.ts
export * from './checkout'
export * from './auth'
export * from './shared'
// every consumer pulls in the world
```

```ts
// ✅ Good — barrel per folder only
// src/checkout/index.ts — local
export * from './Checkout'

// src/index.ts (in a library) — explicit, narrow surface
export { Checkout } from './checkout'
export { Auth } from './auth'
```

**Rule:** barrels are *per-folder*, not *per-app*.

---

## VJS-008 — File and folder naming

Vanilla JS/TS has no community-wide naming convention (unlike React's PascalCase components or Laravel's `*.controller.php`). Pick a convention per project and apply consistently. The defaults below match the rest of this skill:

| Type | Convention | Example |
|---|---|---|
| Class / constructor | `PascalCase.ts` | `Checkout.ts`, `HttpClient.ts` |
| Function module / utility | `kebab-case.ts` | `format-card-number.ts`, `parse-date.ts` |
| Folder (feature, module) | `kebab-case/` | `checkout/`, `auth/`, `http-client/` |
| Public API of a folder | `index.ts` | (always) |
| Types | `types.ts` | (one per folder) |
| Tests | `<name>.test.ts` | `Checkout.test.ts`, `parse-date.test.ts` |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| `src/utils.ts`, `src/helpers.ts` | Junk drawer |
| `src/types.ts` (mega-file) | Types belong next to their owner |
| `src/lib/` with unrelated files inside | Same junk drawer |
| Deep import past a folder's `index.ts` | Breaks encapsulation |
| Single `src/index.ts` re-exporting everything | Kills tree-shaking |
| Tests in `tests/` mirror folder, not next to source | Drift, navigation friction |
| First-use abstraction in `shared/` | Premature; earn the promotion |
| Folder with one file + index.ts re-export | Unnecessary indirection (until second file arrives) |

---

## Review checklist

```
Structure
  □ Top-level src/ contains features and shared/, nothing else
  □ Each multi-file folder has index.ts as public API
  □ shared/ contains only code used by 3+ features
  □ No utils.ts or helpers.ts anywhere

Co-location
  □ Tests live next to source files
  □ Types live next to the code that owns them
  □ Single-use helpers live in the file that uses them

Imports
  □ No deep imports past index.ts
  □ No mega-barrel re-exporting the whole app
  □ Cross-feature dependencies via index.ts only
```
