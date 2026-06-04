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

## How the rules apply to this variant

This variant keeps a per-feature `index.ts` barrel, so ST-003 deep-import is enforced automatically:
`block-ts-violations.py` flags `@/a/b/c` because capability `a/b` exposes that barrel. Nothing to
configure — the presence of the barrel *is* the signal. Every other rule (ST-005 junk-drawer, no-`any`,
naming, arg-count, ST-008 tiers) applies unchanged, as in every layout.

## `.coding-standards-structure` written when chosen

A single `follows:` line — the layout above stays the reference, so it isn't copied into the file:

```yaml
follows: feature-first
```
