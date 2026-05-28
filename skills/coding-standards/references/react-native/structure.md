# React Native / Expo — Architecture

The chosen pattern for React Native and Expo projects: **flat business folders** with ESLint-enforced boundaries. Top-level folders inside `src/` are business capabilities. Each capability has the same internal layout (api, components, hooks, types).

---

## The philosophy in one sentence

> Top-level folders inside `src/` are business capabilities. Each capability has the same internal layout (api, components, hooks, types). Capabilities expose a public API through `index.ts` and never import from each other.

---

## Mandatory shape

```
src/
  app/                              ← router / app entry (file-based or imperative)
    _layout.tsx                     ← root layout (providers)
    index.tsx                       ← home route
    (tabs)/
      _layout.tsx
      home.tsx                      ← imports from capabilities, composes
      discover.tsx
    (auth)/
      sign-in.tsx
    +not-found.tsx

  discussions/                      ← 💬 BUSINESS CAPABILITY
    api/                            ← network layer for this capability
      create-discussion.ts
      get-discussions.ts
      update-discussion.ts
    components/                     ← RN components for this capability
      DiscussionList.tsx
      DiscussionCard.tsx
      CreateDiscussionForm.tsx
    hooks/
      use-discussion.ts
      use-discussion-list.ts
    types/
      index.ts
    utils/
      format-discussion.ts
    index.ts                        ← 🚪 public API

  comments/                         ← 🗨️ BUSINESS CAPABILITY
    api/
    components/
    hooks/
    types/
    index.ts

  identity/                         ← 🔐 BUSINESS CAPABILITY
    api/
    components/
    hooks/
    types/
    index.ts

  components/                       ← SHARED components only
    ui/                             ← design system: Button, Input, Modal
      Button.tsx
      Input.tsx
    layouts/
      Screen.tsx
      Container.tsx

  hooks/                            ← truly shared hooks
    use-keyboard.ts
    use-app-state.ts

  lib/                              ← shared infrastructure
    api-client.ts                   ← HTTP client wrapper
    query-client.ts                 ← server-state cache setup
    storage.ts                      ← device storage wrapper
    notifications.ts                ← push-notifications wrapper

  stores/                           ← global UI state store
    auth-store.ts

  config/
    env.ts                          ← typed env access
    paths.ts

  testing/
    test-utils.tsx
    mocks/

  types/
    global.ts                       ← only truly app-wide types

  utils/                            ← truly shared utilities
```

---

## RN-001 — Top-level folders are business capabilities

| Allowed at the top of `src/` | Forbidden |
|---|---|
| ✅ Business capability folders (`discussions/`, `comments/`, `identity/`) | ❌ `features/` wrapper folder |
| ✅ `app/` (the router/entry layer) | ❌ `screens/` (top-level — couples to navigation, not business) |
| ✅ `components/ui/` (design system primitives) | ❌ A single `src/components/` containing both capability and shared components |
| ✅ `lib/`, `hooks/`, `stores/`, `config/`, `testing/`, `types/`, `utils/` | ❌ Top-level mega-files (`src/types.ts`, `src/utils.ts`) |
|  | ❌ Cross-cutting `services/`, `models/` |

A `features/` wrapper folder adds an extra level for no benefit — opening `src/` should already show you the business. `screens/` as a top-level folder is the same smell: a screen is a *composition* of capability pieces, not its own organizing unit. Let `app/` (or your navigator) own the routes and import from the capabilities.

---

## RN-002 — Every capability has the same internal layout

Predictability is the point. Same five things, every time:

```
<capability>/
  api/                              ← network calls for this capability
  components/                       ← capability-specific RN components
  hooks/                            ← capability-specific hooks
  types/                            ← capability-specific types
  utils/                            ← capability-specific helpers (only when truly local)
  index.ts                          ← public API
```

Add a subfolder only when its first file arrives — but the slot is reserved. When the capability grows from 3 files to 30, you don't refactor; you add files into folders that already exist.

---

## RN-003 — `app/` is thin and composes capabilities into routes

Whether the project uses file-based routing or imperative navigation, the routing layer should only compose pieces from the capabilities — never define business logic.

```tsx
// ✅ Good — app/(tabs)/discover.tsx
import { DiscussionList } from '@/discussions'
import { Screen } from '@/components/layouts'

export default function DiscoverScreen() {
  return (
    <Screen>
      <DiscussionList />
    </Screen>
  )
}

// ❌ Bad — business logic in the route
export default function DiscoverScreen() {
  const { data } = useQuery(['discussions'], () => fetch('https://...'))
  const filtered = data?.filter(d => d.published)
  return <FlatList data={filtered} ... />
}
```

When a route gets non-trivial, **extract the screen as a component inside the relevant capability** and have the route file render that single component.

---

## RN-004 — Capabilities never import from each other

Cross-capability dependencies are forbidden. If capability A needs something from capability B, three options:

1. **It belongs in shared infrastructure** — extract the piece to `lib/`, `components/`, `hooks/`, or `stores/`.
2. **A is built on B** — typically `identity/` is foundational; treat it as a dependency only some capabilities can import (and only via `index.ts`).
3. **Compose them at the route** — `app/` is allowed to use multiple capabilities in one screen.

```tsx
// ❌ Forbidden — comments importing from discussions
// src/comments/components/CommentList.tsx
import { Discussion } from '@/discussions'

// ✅ Allowed — the screen composes both
// app/(tabs)/discussion/[id].tsx
import { DiscussionView } from '@/discussions'
import { CommentList } from '@/comments'

export default function Screen() {
  return <>
    <DiscussionView />
    <CommentList />
  </>
}
```

**Enforce with ESLint's `import/no-restricted-paths`:**

```js
'import/no-restricted-paths': [
  'error',
  {
    zones: [
      // Each capability can be imported only from app/ and from itself
      { target: './src/comments',    from: './src', except: ['./comments',    './app', './lib', './components', './hooks', './stores'] },
      { target: './src/discussions', from: './src', except: ['./discussions', './app', './lib', './components', './hooks', './stores'] },
      // one zone per capability
    ],
  },
]
```

---

## RN-005 — Each capability exposes a narrow `index.ts`

```ts
// src/discussions/index.ts
export { DiscussionList } from './components/DiscussionList'
export { CreateDiscussionForm } from './components/CreateDiscussionForm'
export { useDiscussion } from './hooks/use-discussion'
export type { Discussion } from './types'
// api/, utils/, internal components stay private
```

```ts
// ✅ Allowed
import { DiscussionList } from '@/discussions'

// ❌ Forbidden — deep import past the public API
import { DiscussionList } from '@/discussions/components/DiscussionList'
```

---

## RN-006 — Separate state by **kind**, not by component

State has four distinct kinds; each lives in a different place. Pick whichever libraries the project uses — the rule is about *separation*, not specific tools:

| State kind | Where it lives |
|---|---|
| **Server state** (API responses, cache, mutations) | Capability's `api/` (mutation functions) + `hooks/` (typed query-hook wrappers). Use a server-state cache (sometimes called "data-fetching client" or "async-state library"). |
| **Global UI state** (auth principal, theme, feature flags) | `src/stores/`. Use a small global state store. |
| **Local component state** | Inside the component (`useState` / `useReducer`). |
| **Form state** | Inside the component, or a co-located form hook. Use a form library together with a schema validator. |

**The point:** server state and global state are *different concerns* solved by *different libraries*. Don't store API responses in your global state store. Don't try to use the server-state cache for auth tokens. The two have different invalidation, staleness, and persistence rules.

```ts
// src/discussions/api/get-discussions.ts
export async function getDiscussions(): Promise<Discussion[]> {
  return apiClient.get('/discussions').then(r => r.data);
}

// src/discussions/hooks/use-discussions.ts — wraps the project's server-state cache
export function useDiscussions() {
  return queryHook({ key: ['discussions'], fetcher: getDiscussions });
}
```

The hook shape will vary by library — the principle is that the capability owns the fetcher and the typed hook; the hook is what the components consume.

---

## RN-007 — Platform code via `.ios.tsx` / `.android.tsx`

React Native handles platform divergence with file suffixes — use them when behavior actually differs:

```
components/ui/
  StatusBar.tsx                     ← shared interface
  StatusBar.ios.tsx                 ← iOS-specific implementation
  StatusBar.android.tsx             ← Android-specific implementation
```

Don't scatter `Platform.OS === 'ios'` branches across capability code. If you have one or two `Platform.OS` checks, leave them inline. If you have five or more in one component, split into platform files.

---

## RN-008 — Native modules and Expo plugins isolated

Native modules (Expo plugins, autolinked native code) have a real cost: they break with version mismatches and require rebuilds. Wrap each one behind a `lib/` module so the rest of the app depends on a typed JS interface — not on the native module directly.

```ts
// lib/notifications.ts — the wrapper feature code depends on
import * as Notifications from 'expo-notifications'

export async function scheduleReminder(at: Date, body: string): Promise<string> {
  return Notifications.scheduleNotificationAsync({
    content: { body },
    trigger: { date: at },
  })
}
```

Capabilities import `scheduleReminder`, not `expo-notifications`. If the library changes (or you swap implementations), only `lib/notifications.ts` moves.

---

## RN-009 — Naming

| Type | Convention | Example |
|---|---|---|
| Capability folder | `kebab-case`, plural | `discussions/`, `comments/` |
| Component | `PascalCase.tsx`, **capability-qualified** | `DiscussionList.tsx`, `CreateDiscussionForm.tsx` |
| Hook | `use-kebab-case.ts` | `use-discussion.ts` |
| API call | `verb-kebab-case.ts` | `create-discussion.ts`, `get-discussions.ts` |
| Store (global state) | `*-store.ts` | `auth-store.ts` |
| Library wrapper | `kebab-case.ts` | `api-client.ts`, `notifications.ts` |
| Type file | `index.ts` inside `types/` folder, or `types.ts` | (per feature) |
| Test | `<Name>.test.tsx` | `DiscussionList.test.tsx` |

Generic component names (`Card`, `Modal`, `List`) are forbidden inside capability folders — require a capability qualifier (`DiscussionCard`, `ConfirmDeleteModal`). Generic names are reserved for `components/ui/` (design system primitives).

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| `src/features/` wrapper folder | Adds a useless extra level; top of `src/` should already scream the business |
| Top-level `screens/` folder | Couples organization to navigation; replace with capabilities + thin routes |
| `src/components/` mixing capability and design-system components | Two different things; split into `components/ui/` (shared) and `<capability>/components/` |
| Capability A importing from capability B | Cross-capability coupling; route in `app/` if composition is needed |
| Direct native module imports outside `lib/` | Couples capability code to native lifecycle; wrap it |
| `Platform.OS === 'ios'` branches everywhere | Use `.ios.tsx` / `.android.tsx` suffix files |
| Global state store holding server-cached data | Belongs in the server-state cache, not the UI state store |
| `useEffect(() => { fetch(...) })` in components | Use the data layer (server-state cache + capability's `api/`) |
| Component file at the capability root (outside `components/`) | Should be in `components/` |
| Deep imports past a capability's `index.ts` | Breaks encapsulation |

---

## Review checklist

```
Structure
  □ Top-level src/ folders are business capabilities (no features/ wrapper)
  □ Each capability has api/, components/, hooks/, types/, index.ts (when populated)
  □ components/ui/ holds design-system primitives
  □ lib/ wraps native modules and infrastructure
  □ No screens/ at the top level

Per capability
  □ index.ts declares the public API
  □ Cross-capability imports go through index.ts only
  □ Generic component names live in components/ui/, not in capability folders

Data layer
  □ Server state in the server-state cache
  □ Global UI state in the store
  □ No direct fetch() calls inside components

Platform
  □ Platform-specific code in *.ios.tsx / *.android.tsx
  □ Native modules wrapped behind lib/
```
