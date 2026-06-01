# React Native / Expo — Structure

## Builds on `common/structure.md`

This file adds only what's specific to React Native and Expo (expo-router). The decomposition model —
business → feature → sub-feature → unit, one job per file, front doors, Rule of Three, no junk drawers —
lives in `common/structure.md`, loaded alongside this. Read that for how to organize the inside of any
folder; this file is just the mobile specifics.

## Outer shell

Business capabilities are folders inside `src/` — each one is a top-level area of the product, with its
own components, hooks, server calls, and types. Shared infrastructure (a design-system folder, native-module
wrappers, the data-fetching client) sits beside them, not inside any one capability.

`app/` (expo-router) is **thin**: it owns routing only and composes capabilities into screens. A route file
renders a capability's component and nothing more — no data queries, no business rules, no filtering.

```tsx
// ✅ app/(tabs)/<route>.tsx — renders a capability piece
import { <Feature>List } from '@/<business>'
import { Screen } from '@/components/layouts'
export default function <Route>() { return <Screen><<Feature>List /></Screen> }

// ❌ business logic in the route
export default function <Route>() {
  const { data } = useQuery(['<key>'], () => fetch('https://...'))   // belongs in the capability
  return <FlatList data={data?.filter(x => x.published)} />
}
```

When a route grows past trivial composition, move the screen into a component inside the relevant capability
and have the route render that single component.

## Naming

- **Files** — `kebab-case` (`get-records.ts`, `auth-store.ts`); capability folders `kebab-case`.
- **Components** — `PascalCase.tsx`, domain-qualified: `<Domain>List`, `<Domain>Card`, never bare `Card`.
- **Hooks** — `use-kebab-case.ts`.
- **Server calls, logic, schemas** — `verb-kebab-case.ts`.
- **Co-located** — `<Name>.test.tsx`, `<name>.types.ts`, beside what they describe.
- **Generic names** (`Card`, `Modal`, `Button`, `List`) live only in the design-system folder
  (`components/ui/`), never inside a capability.

## Front door

A capability's public API is its `index.ts` — it re-exports the components, hooks, and types outsiders may
use; `api/` and internal components stay private. Other capabilities import through it and never reach past
it (`common/structure.md`, ST-002/003).

Enforce cross-capability boundaries with ESLint's `import/no-restricted-paths`: each capability is reachable
only from `app/` and from itself. The `except` list must match its own comment — a shared folder (`lib/`,
`components/`) must **not** appear there, or a shared layer could import a capability, inverting the
dependency.

```js
'import/no-restricted-paths': ['error', { zones: [
  // each capability: importable only from app/ and itself — NOT from shared layers
  { target: './src/<business-a>', from: './src', except: ['./<business-a>', './app'] },
  { target: './src/<business-b>', from: './src', except: ['./<business-b>', './app'] },
  // one zone per capability
] }]
```

If capability A genuinely needs something from B: either the piece is shared (lift it to `lib/` /
`components/` / `hooks/`), or A is built on a foundational capability (then list that one in A's `except`),
or compose them at the route in `app/`.

## React Native specifics

- **Separate state by kind, not by component.** Server-cache state (API responses, mutations) lives in the
  capability's `api/` + `hooks/` behind the data-fetching client. Global UI state (auth principal, theme,
  flags) lives in `src/stores/`. Navigation state belongs to the router. Local and form state stay in the
  component. Don't put API responses in the global store, or auth tokens in the server cache — they have
  different staleness, invalidation, and persistence rules.

- **Platform splits via file suffix, not branches everywhere.** When behavior truly differs, use
  `<Name>.ios.tsx` / `<Name>.android.tsx` against a shared interface. One or two inline `Platform.OS` checks
  are fine; five or more in one component means split into platform files.

- **Native modules and Expo config plugins stay behind a wrapper.** Native code breaks on version mismatch
  and forces rebuilds. Wrap each module in a `lib/` file exposing a typed JS interface; capabilities import
  that wrapper, not the native package directly. Swapping or upgrading the library then touches only the
  one wrapper.
