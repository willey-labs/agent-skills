# Next.js — `feature-first`

**Organize by capability.** Each feature is a self-contained module under `src/features/`. The router (`app/`) stays thin and *composes* features. Shared code sits at the top level.

Source: [bulletproof-react](https://github.com/alan2207/bulletproof-react) — the most-referenced scalable React/Next structure. Folder names below are verbatim from its `docs/project-structure.md`.

> This variant follows `common/structure.md` for the inside of every folder; everything below is just its outer shape — where each feature's folder sits and how it exposes its public surface.

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
deep-import (ST-003): ON       # enforce the per-feature index.ts boundary — the only variant-driven toggle (god-file is a separate project-level advisory)
universal rules:      ON       # ST-005 junk-drawer, no-any, naming, arg-count, ST-008 tiers — mandatory, never per-variant
```

## `.coding-standards-structure` written when chosen

Recording the choice is a single `follows:` line — the layout above stays the reference, so it isn't copied into the file. This variant keeps per-feature barrels, so `deep-import` stays on (the default) and needs no toggle:

```yaml
follows: feature-first
```
