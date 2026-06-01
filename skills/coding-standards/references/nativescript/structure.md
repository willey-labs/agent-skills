# NativeScript — Structure

## Builds on `common/structure.md`

This file adds only what's specific to NativeScript (JavaScript/TypeScript native mobile). The
decomposition model — business → feature → sub-feature → unit, one job per file, variants as
one-interface-per-form, every ST rule — lives in `common/structure.md`, loaded alongside this. Read that
first; this file is just the NativeScript specifics.

## Outer shell

NativeScript lets you name the top folders, so business goes straight to the top of `app/`. NativeScript
apps are screen-and-navigation-centric, so the top-level folders inside `app/` are business capabilities
(`<capability>/`), not technical layers (no top-level `views/`, `services/`, or `models/` holding every
screen or service together). To find everything for one capability, open one folder — no `features/`
wrapper, since the top of `app/` already names the business.

The framework keeps a few fixed entries at the top: `app.ts` (bootstrap), `app-root.xml` (root navigation
frame), `app.css` (global styles, used sparingly), plus `assets/` and `fonts/` by convention. Everything
else is yours to name by meaning.

## Naming

- **Folders** — `kebab-case`: `<capability>/`.
- **Classes** — `PascalCase` (view models, services): `<Capability>ViewModel`, `<Capability>Service`.
- **Page-and-view-model pairing** — a page is a file group sharing one `kebab-case` stem:
  - `<screen>-page.xml` — markup
  - `<screen>-page.ts` — code-behind (page event handlers)
  - `<screen>-page-view-model.ts` — the view model (state + behavior)
- **Reusable component within a capability** — `<name>.xml` + `<name>.ts` (no `-page` suffix).
- **Services** — `<name>-service.ts`; persistence — `<name>-repository.ts`.
- **Platform-specific** — `<name>.android.ts` / `<name>.ios.ts`.
- **Generic names** (`Card`, `Modal`, loading/empty/error) live only in the shared UI layer, never inside
  a capability (`common/structure.md`, ST-006).

## Front door

A folder's public API is its `index.ts` (re-exports the public symbols). Other folders import through it
and never reach past it (`common/structure.md`, ST-002/003). One capability needing something from another
goes through that capability's `index.ts`, and only for an export deliberately added there:

```ts
import { Thing } from '@/<capability>'              // ✅
import { Thing } from '@/<capability>/services/...'  // ❌ deep import
```

## NativeScript specifics

- **A page and its view model are one unit.** The `.xml`, `.ts`, and `-view-model.ts` files for a
  screen always sit together in the same folder — never split into parallel `xml/`, `ts/`, `view-models/`
  trees. Opening the folder shows the whole screen.

- **View models hold state and behavior; the page only dispatches and binds.** The code-behind
  (`*-page.ts`) creates the view model, sets the binding context, and forwards events — nothing more. No
  data fetching, no transforming, no business rules in the code-behind; that work lives in the view model.
  An event handler that uses `await` must be declared `async`.

- **Services own external interactions.** API calls, persistence, and platform APIs go in the
  capability's `services/` folder — never inside a view model or page directly. View models depend on a
  service, not on `fetch` (`code-principles.md` DP-005). Offline handling, retries, and error shaping live
  here, where they can be reused and tested without a page.

- **Platform differences hide behind one import.** When behavior diverges between iOS and Android,
  use platform-suffix files (`<name>.android.ts` / `<name>.ios.ts` behind a shared declaration) or a
  helper in `shared/platform/`. Do not scatter `if (isAndroid)` / `if (isIOS)` branches through capability
  code.

- **Navigation happens at composition points, not inside view models.** `Frame.navigate()` couples
  a view model to a route. Keep it out of view models: the view model exposes intent (a callback or event),
  and the page-level code performs the navigation. This keeps view models testable and makes the navigation
  graph visible at the page.
