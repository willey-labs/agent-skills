# Vue / Nuxt — Structure

## Builds on `common/structure.md`

This file adds only what's specific to Vue 3 / Nuxt 3. The decomposition model — business → feature →
sub-feature → unit, one job per file, front doors, Rule of Three, no junk drawers — lives in
`common/structure.md`, loaded alongside this. Read that for how to organize the inside of any folder.

## Outer shell

Top-level folders are business capabilities (`<business>/`, `<other-business>/`), each owning its own
`components/`, `composables/`, `stores/`, and `api/`. The router (Vue Router) or `pages/` (Nuxt) is the
routing layer only — a route picks a capability piece and renders it, nothing more.

Nuxt auto-imports the project-root `composables/`, `components/`, and `utils/` folders. That tempts you to
dump everything there — don't. **Those auto-import folders are for the design system and truly cross-cutting
code only.** Capability code lives in capability folders (which Nuxt does *not* auto-import) and is imported
explicitly through the capability's front door.

**Nuxt 4 moved the default source dir to `app/`** (stable since mid-2025; Nuxt 3 reaches EOL in 2026). The
architecture is unchanged, but the auto-import folders now sit under `app/` (`app/composables/`,
`app/components/`, …). Check whether the project root or `app/` holds them before deciding where a file goes.

## Naming

- **Components** — `PascalCase.vue`, domain-qualified inside a capability: `<Domain>List`, `<Domain>Card`,
  never bare `Card`. Generic primitives (`Card`, `Modal`, `Button`) live only in the design-system folder
  (`shared/ui/`, or the auto-imported `components/`), typically with a project-wide prefix (`App*`, `Base*`).
- **Composables** — file `use-kebab-case.ts`, export `useCamelCase` (e.g. `use-<thing>.ts` → `use<Thing>`).
- **Pinia stores** — file `<name>-store.ts`, export `use<Name>Store`.
- **API calls** — `verb-kebab-case.ts` (`get-<noun>.ts`, `create-<noun>.ts`).
- **Capability folders** — `kebab-case`, plural.

## Front door

A capability's public API is its `index.ts` — it re-exports the public components, composables, and types;
everything else (api/, internal components) stays private. Other capabilities import `from '@/<business>'`
and never reach past it (`common/structure.md` ST-002/003). Cross-capability composition happens at the
page layer, not by one capability importing another's internals.

```ts
// <business>/index.ts
export { default as <Domain>Detail } from './components/<Domain>Detail.vue'
export { use<Domain> } from './composables/use-<domain>'
export type { <Domain> } from './types'
```

## Vue / Nuxt specifics

- **Composition API with `<script setup lang="ts">` only for new code.** No Options API
  (`data()`, `methods: {}`, `computed: {}`) in a Composition-API project. Options API is acceptable only
  when maintaining an un-migrated Vue 2 codebase. `<script setup>` gives prop/emit type inference and groups
  logic by concern, not by lifecycle hook. Type `defineProps` and `defineEmits`.

- **Composables are the unit of logic reuse** — one per file, name starts with `use`, returns
  plain reactive primitives (`ref`/`computed`/functions), never a class with internal state. **Inside a
  composable, import everything it uses** (`ref`, `computed`, `watchEffect`, `toValue`, `MaybeRefOrGetter`,
  …) — library code must not lean on Nuxt auto-import. For data fetching, wrap a dedicated library
  (TanStack Query, Nuxt `useFetch`/`useAsyncData`) in a named composable rather than hand-rolling
  `watchEffect` + `fetch`.

  ```ts
  // <business>/composables/use-<domain>.ts — explicit imports, no auto-import reliance
  import { ref, watchEffect, toValue, type MaybeRefOrGetter } from 'vue'
  import { get<Domain> } from '../api/get-<domain>'
  import type { <Domain> } from '../types'

  export function use<Domain>(id: MaybeRefOrGetter<string>) {
    const item = ref<<Domain> | null>(null)
    watchEffect(async () => { item.value = await get<Domain>(toValue(id)) })
    return { item }
  }
  ```

- **Separate state by kind, not by component.** Server state (API responses, cache) → a
  data-fetching library, wrapped per query in a named composable. Global UI state (auth, theme, flags) →
  a Pinia store. Local state → `ref`/`reactive` in the component. Form state → a form library or co-located
  composable. **Pinia is for UI state, not server state** — storing API responses in Pinia makes it a cache
  with no invalidation rules.

- **Pages are thin; they compose capability pieces.** A page (or router route) reads route params
  and renders a capability component (e.g. the `<Domain>Detail` the front door above exports) — no data
  fetching, no business rules. When a page grows non-trivial, extract a `<…Screen />` component inside the
  capability and have the page render that one component.

- **Nuxt server routes stay thin too.** `server/api/` is a Node backend: a handler parses input,
  calls a service, shapes the response — no business logic in the route file. For non-trivial server logic,
  structure `server/` per-feature like a Node backend (`references/node-express/structure.md`). For a tiny
  backend, the route file being the whole story is fine.
