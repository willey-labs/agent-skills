# Next.js — `feature-sliced-design`

**A formal, strictly-specified methodology.** Code is split into ordered **layers**, each partitioned into **slices** (by business domain), each split into **segments** (by technical purpose). A module may import only from layers strictly below it.

Source: [feature-sliced.design](https://feature-sliced.design). Names below are the methodology's **official** vocabulary — used verbatim.

## Layers (top imports from below; never upward)

```
src/
  app/        # everything that makes the app run — routing, entrypoints, providers, global styles
  pages/      # full pages or large parts of a page in nested routing
  widgets/    # large self-contained chunks of UI delivering an entire use case
  features/   # reused implementations of product features (actions that bring business value)
  entities/   # business entities the project works with (e.g. user, product)
  shared/     # reusable functionality detached from project specifics
```

(`processes/` — cross-page scenarios — exists but is **deprecated**; omit it.)

## Slices and segments

- **Slice** = a folder inside a layer, named by business domain: `entities/user/`, `features/auth/`, `widgets/order-summary/`. Slices in the same layer may not import each other.
- **Segment** = a folder inside a slice, named by purpose. Official segment names:

```
<layer>/<slice>/
  ui/       # UI components, formatters, styles
  api/      # backend interactions, request functions, data types
  model/    # schemas, stores, business logic
  lib/      # library code used by this slice
  config/   # configuration and feature flags
```

## Import rule

> A module may import only from layers **strictly below** it.

`app → pages → widgets → features → entities → shared`. This is the methodology's core invariant; it prevents cycles and keeps changes localized. Enforce with `@feature-sliced/eslint-config` or the **Steiger** linter.

## Hooks this variant implies

```yaml
deep-import (ST-003): ON       # cross-slice / public-API boundaries enforced
junk-drawer (ST-005): ON       # "lib" segment is intentional, not a dumping ground
tests (ST-007):       ON
common rules:         ON
```

> Note: FSD's `app/` layer is the whole application shell (routing + providers), which in a Next.js App Router project overlaps with the framework's own `app/` directory. Teams typically keep Next.js's `app/` as the route layer and place FSD layers under `src/` — confirm this mapping with the user when this variant is chosen.

## `.coding-standards-structure` written when chosen

```yaml
framework: nextjs
variant: feature-sliced-design
source: feature-sliced.design
layers: [app, pages, widgets, features, entities, shared]   # processes deprecated
slice: by business domain within a layer
segments: [ui, api, model, lib, config]
imports:
  rule: "import only from layers strictly below"
  enforce: "@feature-sliced/eslint-config or steiger"
hooks:
  deep-import: on
  junk-drawer: on
  tests-colocated: on
```
