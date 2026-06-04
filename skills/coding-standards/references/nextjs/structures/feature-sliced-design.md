# Next.js — `feature-sliced-design`

**A formal, strictly-specified methodology.** Code is split into ordered **layers**, each partitioned into **slices** (by business domain), each split into **segments** (by technical purpose). A module may import only from layers strictly below it.

Source: [feature-sliced.design](https://feature-sliced.design). Names below are the methodology's **official** vocabulary — used verbatim.

> This variant follows `common/structure.md` for the inside of every folder (segment); everything below is just its outer shape — the layers, slices, and import direction.

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

- **Slice** = a folder inside a layer, named by business domain: `entities/<entity>/`, `features/<feature>/`, `widgets/<widget>/`. Slices in the same layer may not import each other.
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

## How the rules apply to this variant

FSD's public-API segments are barrels, so ST-003 deep-import is enforced automatically across slice and
public-API boundaries: `block-ts-violations.py` flags a deep import because the capability exposes that
segment. Nothing to configure — the barrel *is* the signal. Every other rule (ST-005 junk-drawer,
no-`any`, naming, arg-count, ST-008 tiers) applies unchanged, as in every layout.

> Note: FSD's `app/` layer is the whole application shell (routing + providers), which in a Next.js App Router project overlaps with the framework's own `app/` directory. Teams typically keep Next.js's `app/` as the route layer and place FSD layers under `src/` — confirm this mapping with the user when this variant is chosen.

## `.coding-standards-structure` written when chosen

A single `follows:` line — the layout above stays the reference, so it isn't copied into the file:

```yaml
follows: feature-sliced-design
```
