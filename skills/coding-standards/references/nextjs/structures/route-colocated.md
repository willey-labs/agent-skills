# Next.js — `route-colocated`

**Organize primarily by route.** A feature's code lives inside its own App Router segment. Anything reused across routes is promoted to a top-level shared folder. There is no `src/<capability>/` layer — the route segment *is* the feature boundary.

This is the most common modern Next.js App Router layout.

> This variant follows `common/structure.md` for the inside of every folder; everything below is just its outer shape — where feature code sits and how it's promoted to shared.

## Layout

```
src/
  app/                         # routing — App Router segments are the app's pages
    <segment>/                 # ONE route; its UI + logic + data live here, colocated
      page.tsx  layout.tsx
      _<name>/                 # route-private pieces (leading "_" = not a route)
    layout.tsx  page.tsx  globals.css
  components/                  # shared UI — reused by 2+ routes
    ui/                        # design system / UI primitives (shadcn/ui) — owned by the generator
    <domain>/                  # optional domain buckets (e.g. chat/, settings/)
  lib/                         # shared utility + infrastructure code, not tied to one feature
    <domain>/                  #   domain-scoped helpers
    utils/  config/  clients/  #   cross-feature helpers, config, external clients
    *.query.ts                 #   data-fetching hooks (server-state)
```

## Conventions

- **Files:** `kebab-case`. Optional suffix taxonomy, kept only if the repo already uses it: `*.query.ts` (data fetching), `*.hook.ts` (hook).
- **Components:** `PascalCase`, domain-qualified — `<Domain>Card`, not bare `Card`. Generic names only inside `components/ui/`.
- **Promotion:** start inside the route segment → promote to `components/` or `lib/` when a second route needs it.
- **Barrels:** none — routes import what they need directly.
- **Tests:** colocated (`*.test.tsx`) next to the file under test.

## Hooks this variant implies

```yaml
deep-import (ST-003): OFF      # no index.ts barrels in this layout — the only variant-driven toggle (god-file is a separate project-level advisory)
universal rules:      ON       # ST-005 junk-drawer, no-any, naming, arg-count, ST-008 tiers — mandatory, never per-variant
```

## `.coding-standards-structure` written when chosen

Recording the choice is a single `follows:` line — the layout above stays the reference, so it isn't copied into the file. This variant is barrel-less, so it also sets the `deep-import` toggle off:

```yaml
follows: route-colocated
hooks:
  deep-import: off               # barrel-less layout — ST-003 has nothing to check
```
