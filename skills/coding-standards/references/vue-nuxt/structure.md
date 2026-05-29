# Vue / Nuxt — Architecture

The chosen pattern for Vue 3 / Nuxt 3 projects: **flat business folders** with composition-API single-file components, Pinia for global state, composables for shared logic. Same shape as Next.js / React Native, adapted to Vue idioms.

> **Nuxt 4 note** (current stable since mid-2025; Nuxt 3 reaches EOL in 2026): the architecture below is unchanged, but Nuxt 4 moved the default source directory to `app/`. The project-root auto-import folders shown here (`composables/`, `components/`, `utils/`) live under `app/` by default in Nuxt 4 — read those paths as `app/composables/` etc. when on Nuxt 4.

---

## The philosophy in one sentence

> Top-level folders inside `src/` (or the project root for Nuxt) are business capabilities. Each capability owns its `.vue` components, composables, stores, and types, and exposes them via `index.ts`. The router/pages are thin and compose capability pieces.

---

## Builds on `common/structure.md`

This file specializes the universal structural rules in `references/common/structure.md`. Vue and Nuxt add SFC-specific concerns: composition API over options API, composables as the unit of reuse, the script/template/style separation, Pinia for state, and Nuxt's file-based routing. Read `common/structure.md` first.

---

## Mandatory shape

```
# Vanilla Vue 3 (Vite)
src/
  main.ts                            ← bootstrap (createApp, plugins, mount)
  App.vue                            ← root component
  router/
    index.ts                         ← route definitions composing capability pieces

  appointments/                      ← 📅 BUSINESS CAPABILITY
    components/
      AppointmentList.vue
      AppointmentCard.vue
      BookAppointmentForm.vue
    composables/                     ← reusable composition functions (use*)
      use-appointment.ts
      use-appointment-list.ts
    stores/                          ← Pinia stores (when needed)
      appointments-store.ts
    api/                             ← network calls (REST or GraphQL)
      list-appointments.ts
      book-appointment.ts
    types.ts
    index.ts                         ← 🚪 public API

  prescriptions/
    ...

  shared/
    ui/                              ← design-system primitives
      AppButton.vue                  ← generic — usable across capabilities
      AppInput.vue
      AppModal.vue
    composables/                     ← cross-cutting composables
      use-media-query.ts
      use-debounce.ts
    lib/
      http-client.ts
      date.ts
    config/
      env.ts
    types/
      global.ts
```

**For Nuxt 3**, the layout uses Nuxt's auto-imported conventions:

```
project_root/
  app.vue                              ← root
  nuxt.config.ts

  pages/                               ← file-based routes — thin, compose capabilities
    appointments/
      index.vue
      [id].vue
      book.vue
    auth/
      sign-in.vue

  appointments/                        ← capability folder (not auto-imported by Nuxt)
    components/
    composables/
    stores/
    api/
    types.ts
    index.ts

  server/                              ← Nuxt server routes & API
    api/
      appointments/
        index.get.ts
        [id].get.ts

  composables/                         ← Nuxt auto-imports — for truly cross-cutting only
    use-current-user.ts

  components/                          ← Nuxt auto-imports — for design-system primitives only
    AppButton.vue
    AppCard.vue
```

**Important Nuxt nuance:** Nuxt 3 auto-imports the contents of `composables/`, `components/`, and `utils/` at the project root. That's convenient but tempts you to dump everything there. **Restrict the auto-import folders to the design system / truly cross-cutting code only.** Capability code lives in capability folders (`appointments/`, `prescriptions/`) which are *not* auto-imported — consumers import explicitly through the capability's `index.ts`.

---

## VN-001 — Top-level folders are business capabilities

Same as the rest of this skill. See `common/structure.md` ST-001 for the universal rule and how to test it.

| ✅ Allowed at the top of `src/` | ❌ Forbidden |
|---|---|
| Business capability folders (`appointments/`, `prescriptions/`) | `components/`, `composables/`, `stores/` as top-level (Vue 3 vanilla) |
| `router/`, `shared/`, `main.ts`, `App.vue` | A single `views/` or `pages/` folder masquerading as the organization |
| For Nuxt: `pages/`, `server/`, `app.vue`, `nuxt.config.ts`, plus capability folders | `features/` wrapper folder |

**Nuxt-specific:** the auto-imported `composables/`, `components/`, `utils/` at the project root are **design-system only** — not the dumping ground for capability code. A capability composable lives at `appointments/composables/use-appointment.ts` and is imported by path, not auto-imported.

---

## VN-002 — Composition API only; no Options API for new code

Vue 3 has two component APIs: the older **Options API** (`data() { ... }`, `methods: { ... }`, `computed: { ... }`) and the newer **Composition API** (`<script setup>`, `ref`, `computed`, `watch`). For new code, use Composition API with `<script setup>`.

```vue
<!-- ✅ Good — Composition API with <script setup> -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppointment } from '../composables/use-appointment'

const props = defineProps<{ appointmentId: string }>()
const { appointment, isLoading } = useAppointment(props.appointmentId)
const formattedDate = computed(() => formatDate(appointment.value?.scheduledAt))
</script>

<template>
  <article v-if="!isLoading && appointment">
    <h2>{{ appointment.doctor.name }}</h2>
    <time>{{ formattedDate }}</time>
  </article>
</template>
```

**Why Composition API is the right default:**

- **Composables replace mixins** — reusable logic packages cleanly without name collisions.
- **Type inference is sharper** — `<script setup lang="ts">` infers prop and emit types from `defineProps` / `defineEmits`.
- **Logic groups by concern, not by lifecycle hook** — related code (state + computed + side effects for one feature) lives together instead of being scattered across `data()`, `computed: {}`, `mounted()`.

**When Options API is acceptable:** maintaining an existing Vue 2 codebase that hasn't been migrated. Don't introduce new Options API components in a Composition API project.

---

## VN-003 — Composables are the unit of logic reuse

A composable is a function that uses other composables (`useRoute`, `ref`, etc.) and returns reactive state + behavior. Composables are to Vue what hooks are to React — but they're plain functions, no rules-of-hooks ceremony.

```ts
// appointments/composables/use-appointment.ts
import { ref, watchEffect } from 'vue'
import { getAppointment } from '../api/get-appointment'
import type { Appointment } from '../types'

export function useAppointment(id: MaybeRefOrGetter<string>) {
  const appointment = ref<Appointment | null>(null)
  const isLoading = ref(true)
  const error = ref<Error | null>(null)

  watchEffect(async () => {
    isLoading.value = true
    try {
      appointment.value = await getAppointment(toValue(id))
    } catch (e) {
      error.value = e as Error
    } finally {
      isLoading.value = false
    }
  })

  return { appointment, isLoading, error }
}
```

**Rules:**

- One composable per file, named `use-kebab-case.ts`.
- Composable name starts with `use`: `useAppointment`, `useDebounce`, `useMediaQuery`.
- A composable returns plain reactive primitives (`ref`, `computed`, functions) — never a class with internal state.
- For data fetching, **prefer a dedicated data-fetching library** (TanStack Query, Nuxt's `useFetch`/`useAsyncData`) over hand-rolled `watchEffect + fetch`. Wrap the library call in a named composable per query.

---

## VN-004 — Separate state by kind, not by component

Same rule as `references/react-native/structure.md` RN-006. Four kinds of state, each in its own home:

| State kind | Where it lives |
|---|---|
| **Server state** (API responses, cache, mutations) | A data-fetching library (TanStack Query Vue, Nuxt `useFetch` / `useAsyncData`). Wrap in a named composable per query. |
| **Global UI state** (auth principal, theme, feature flags) | Pinia store (`stores/auth-store.ts`). |
| **Local component state** | `ref`/`reactive` inside the component or composable. |
| **Form state** | `vee-validate`, `formkit`, or a co-located composable. Don't store form state in a Pinia store. |

**Pinia is for UI state, not server state.** Storing API responses in Pinia turns it into a cache with no invalidation rules. Use TanStack Query (or equivalent) for server state instead — it has built-in stale-while-revalidate, retries, and cache invalidation.

```ts
// ✅ Good — Pinia for auth UI state
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => user.value !== null)
  function setUser(u: User) { user.value = u }
  function clearUser() { user.value = null }
  return { user, isAuthenticated, setUser, clearUser }
})
```

```ts
// ❌ Bad — Pinia holding server data
export const useAppointmentsStore = defineStore('appointments', () => {
  const list = ref<Appointment[]>([])  // server state masquerading as UI state — invalidation nightmare
  async function load() { list.value = await fetchAppointments() }
  return { list, load }
})
```

---

## VN-005 — Pages are thin; they compose capability pieces

Vue Router routes (or Nuxt pages) are the routing layer. **No business logic.** A page imports capability components, wires up route params, and renders them.

```vue
<!-- ✅ Good — pages/appointments/[id].vue (Nuxt) -->
<script setup lang="ts">
import { AppointmentDetail } from '~/appointments'

const route = useRoute()
const appointmentId = computed(() => route.params.id as string)
</script>

<template>
  <AppointmentDetail :id="appointmentId" />
</template>

<!-- ❌ Bad — business logic inside the page -->
<script setup lang="ts">
const route = useRoute()
const { data: appointment } = await useFetch(`/api/appointments/${route.params.id}`)
const status = computed(() => (appointment.value?.cancelledAt ? 'cancelled' : 'active'))
// ... 80 more lines of behavior
</script>
```

When a page grows non-trivial, extract a `<CapabilityScreen />` component inside the capability and have the page render that single component.

---

## VN-006 — Capability `index.ts` is the public API

Each capability folder exports its public surface from `index.ts`:

```ts
// appointments/index.ts
export { default as AppointmentList } from './components/AppointmentList.vue'
export { default as BookAppointmentForm } from './components/BookAppointmentForm.vue'
export { useAppointment } from './composables/use-appointment'
export type { Appointment, AppointmentStatus } from './types'
// api/, internal components stay private
```

Consumers import `from '@/appointments'`. Deep imports past the public API are forbidden (see `common/structure.md` ST-003).

**Forbidden in capability components:**

- `import { Prescription } from '@/prescriptions/types'` — cross-capability internal import.
- `import { CommentList } from '@/comments/components/CommentList.vue'` — deep import past `index.ts`.

Cross-capability composition happens **at the page layer**, not inside another capability.

---

## VN-007 — Component naming is domain-qualified

```
appointments/components/
  AppointmentList.vue           ← domain-qualified ✅
  AppointmentCard.vue           ← domain-qualified ✅
  AppointmentBookingDialog.vue  ← domain-qualified ✅
  Card.vue                      ← generic, wrong folder ❌

shared/ui/
  AppCard.vue                   ← prefixed primitive, design system ✅
  AppModal.vue                  ← prefixed primitive ✅
```

Generic component names belong in the design-system folder (`shared/ui/` for vanilla Vue, top-level `components/` for Nuxt auto-import). Inside a capability folder, component names must include the capability or a domain noun.

**The `App` prefix** for design-system components is a common Vue convention that avoids the rare collision with native HTML elements. Either commit to it project-wide or pick another consistent prefix (e.g., `Base*`, the capability's design-system family).

---

## VN-008 — Vue-specific file & folder naming

| Type | Convention | Example |
|---|---|---|
| Capability folder | `kebab-case`, plural | `appointments/`, `prescriptions/` |
| Component file | `PascalCase.vue`, domain-qualified | `AppointmentList.vue`, `BookAppointmentForm.vue` |
| Design-system component | `PascalCase.vue`, prefixed | `AppButton.vue`, `AppModal.vue` |
| Composable file | `use-kebab-case.ts` | `use-appointment.ts`, `use-debounce.ts` |
| Composable export | `useCamelCase` | `useAppointment`, `useDebounce` |
| Pinia store file | `*-store.ts` | `auth-store.ts`, `feature-flags-store.ts` |
| Pinia store export | `useCamelCaseStore` | `useAuthStore` |
| API call | `verb-kebab-case.ts` | `book-appointment.ts`, `get-appointments.ts` |
| Page file (Nuxt) | follows Nuxt convention | `pages/appointments/[id].vue` |
| Type file | `types.ts` (per capability) | `types.ts` |

---

## VN-009 — Nuxt server routes are thin too

Nuxt 3's `server/api/` folder is a Node backend. **The same rules apply:** server routes are thin handlers that parse input, call a service, and shape the response. Business logic does not live in `server/api/appointments/[id].get.ts`.

For a Nuxt project with non-trivial server logic, structure `server/` like a Node-Express backend (`references/node-express/structure.md`): per-feature folders with `routes/`, `service/`, `repository/`, mounted via Nuxt's per-file route conventions. Or, for very small backends, accept that the route file is the whole story and move on.

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Options API in new code | Composition API is the framework's current direction |
| Logic in `<script>` blocks instead of composables | Reuse is impossible without `<script setup>` + composables |
| Pinia stores holding server data | Server state belongs in a data-fetching cache |
| `useFetch` / `fetch` calls inside components instead of composables | Wrap data-fetching calls in named composables |
| Cross-capability component imports (`from '@/prescriptions/components/...'`) | Deep import past index.ts |
| Capability-specific component in `shared/ui/` | Design-system folder is for generic primitives only |
| Generic component name inside a capability (`Card.vue`) | Domain-qualify |
| Nuxt `composables/` folder used for capability composables | Auto-import folder is design-system only |
| Page file with business logic | Extract a `<CapabilityScreen />` component |
| `defineEmits()` without a typed event list | Lose IDE help; lose runtime checks |
| Two-way `v-model` on complex objects without a clear contract | Hard to track state changes; prefer prop + emit pairs |
| Pinia store and component sharing mutable references freely | Treat store state as opaque to consumers; mutate via store actions |

---

## Review checklist

```
Structure
  □ Top-level folders are capabilities, not technical layers
  □ Capabilities own components, composables, stores, api/
  □ shared/ for cross-cutting code used by 3+ capabilities
  □ Nuxt: auto-imported composables/ and components/ are design-system only

Components
  □ <script setup lang="ts"> (Composition API)
  □ Component names PascalCase, domain-qualified inside capabilities
  □ defineProps and defineEmits are typed

Composables
  □ One composable per file (use-kebab-case.ts)
  □ Composable names start with `use`
  □ Composable returns refs/computeds, not classes
  □ Data-fetching wrapped via TanStack Query / useFetch + named composable

State
  □ Pinia stores hold UI state only
  □ Server state in a data-fetching cache
  □ Local state inside the component or composable
  □ Form state via a form library or co-located composable

Imports
  □ Cross-capability imports go through index.ts
  □ No deep imports past index.ts
  □ Pages compose capability pieces; no business logic in pages

Naming
  □ Components: PascalCase, domain-qualified or App-prefixed
  □ Composables: use-kebab-case file → useCamelCase export
  □ Stores: *-store.ts file → useCamelCaseStore export
  □ API calls: verb-kebab-case.ts
```
