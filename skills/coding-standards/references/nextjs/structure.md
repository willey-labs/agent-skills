# Next.js — Structure

## Builds on `common/structure.md`

This file adds only what's specific to Next.js (App Router). The decomposition model — business →
feature → sub-feature → unit, one job per file, variants as one-interface-per-form, all the ST rules —
lives in `common/structure.md`, loaded alongside this. Read that for how to organize the inside of any
folder; this file is just the Next.js specifics.

## Outer shell

Next.js owns `app/` (routing). Where business code sits is a one-time choice from the catalog in
`structures/`:

- `route-colocated` — feature code inside its own `app/<segment>/` (no `src/<business>/` layer)
- `feature-first` — `src/features/<feature>/`
- `screaming-architecture` *(default)* — `src/<business>/<feature>/` with a fixed inner shape
- `feature-sliced-design` — layered slices

Pick the one the team uses and follow it. Whichever shell is picked, the inside of every folder follows
`common/structure.md` — that part doesn't change between shells.

## Naming

- **Components** — `PascalCase.tsx`, domain-qualified: `<Domain>Card`, never bare `Card`.
- **Hooks** — `use-kebab-case.ts`.
- **Logic, server calls, schemas** — `verb-kebab-case.ts`.
- **Co-located** — `<name>.test.tsx`, `<name>.types.ts`, `<name>.stories.tsx`, beside what they describe.
- **Generic names** (`Card`, `Modal`, `Button`) live only in the design-system folder (`shared/ui/` or
  `components/ui/`), never inside a feature.

## Front door

A folder's public API is its `index.ts` (re-exports the public symbols). Other folders import through it
and never reach past it (`common/structure.md`, ST-002/003).

## Next.js specifics

- **`app/` is the router — keep it thin.** It does routing and composition only: no data queries, no
  business rules. A route renders a feature's component and nothing else.
  ```tsx
  // ✅ app/<segment>/page.tsx — renders a feature
  import { Feature } from '@/<business>/<feature>'
  export default function Page() { return <Feature /> }

  // ❌ business logic in the route
  export default async function Page() {
    const rows = await db.query(...)        // no — belongs in the feature's server file
    return <form>...</form>
  }
  ```
  Route groups `(group)/`, private folders `_internal/`, `api/.../route.ts`, and `layout.tsx` are routing
  structure — they live in `app/`, not in the business folders.

- **Server Components are the default; keep `'use client'` low.** Add `'use client'` only on the components
  that truly need interactivity, as low in the tree as possible — don't mark a whole feature client just to
  make one button work. Data fetching and server actions live in the feature's server-side files (e.g. its
  `api/`), never inside a client component.
