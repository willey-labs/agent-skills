# Next.js — `feature-first`

**Organize by capability.** Each feature is a self-contained module under `src/features/`. The router (`app/`) stays thin and *composes* features. Shared code sits at the top level.

Source: [bulletproof-react](https://github.com/alan2207/bulletproof-react) — the most-referenced scalable React/Next structure. Folder names below are verbatim from its `docs/project-structure.md`.

## Layout

```
src/
  app/                         # routing — thin segments that compose features
  features/
    <feature>/                 # one business capability, self-contained
      api/                     # API request declarations + hooks for the feature
      components/              # components scoped to the feature
      hooks/                   # feature-scoped hooks
      stores/                  # state stores for the feature
      types/                   # types within the feature
      utils/                   # utilities for the feature
      index.ts                 # the feature's public surface
  components/                  # shared UI across the app
  hooks/                       # shared hooks
  lib/                         # preconfigured reusable libraries
  stores/                      # global state stores
  config/                      # global config + env
  types/                       # shared types
  utils/                       # shared utilities
  testing/  assets/
```

> Not every feature needs every subfolder — include only the ones it uses.

## Conventions

- **Files:** `kebab-case`; **Components:** `PascalCase`, domain-qualified.
- **Public surface:** each feature exposes its API through `features/<feature>/index.ts`; other code imports the feature, never its internals.

## Import rule (bulletproof-react)

```
shared  →  features  →  app
```

- Features **never import from other features** — compose them at the `app/` level.
- Shared modules (`components`, `hooks`, `lib`, `types`, `utils`) may not import from `features` or `app`.
- Enforce with ESLint `import/no-restricted-paths`.

## Hooks this variant implies

```yaml
deep-import (ST-003): ON       # enforce the per-feature index.ts boundary
junk-drawer (ST-005): ON       # feature/shared utils OK, but no bare utils.ts dumping ground
tests (ST-007):       ON
common rules:         ON
```

## `.coding-standards-structure` written when chosen

```yaml
framework: nextjs
variant: feature-first
source: bulletproof-react
where:
  routing:       app/
  feature:       src/features/<feature>/
  feature-parts: [api, components, hooks, stores, types, utils]
  feature-public-api: src/features/<feature>/index.ts
  shared-ui:     src/components/
  shared-logic:  src/lib/
  shared-hooks:  src/hooks/
  global-state:  src/stores/
  config:        src/config/
imports:
  rule: "shared -> features -> app"
  cross-feature: forbidden
hooks:
  deep-import: on
  junk-drawer: on
  tests-colocated: on
```
