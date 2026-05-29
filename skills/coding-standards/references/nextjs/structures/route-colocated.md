# Next.js — `route-colocated`

**Organize primarily by route.** A feature's code lives inside its own App Router segment. Anything reused across routes is promoted to a top-level shared folder. There is no `src/<capability>/` layer — the route segment *is* the feature boundary.

This is the most common modern Next.js App Router layout, and the one Archestra's frontend uses.

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
- **Components:** `PascalCase`, domain-qualified — `AppointmentCard`, not `Card`. Generic names only inside `components/ui/`.
- **Promotion:** start inside the route segment → promote to `components/` or `lib/` when a second route needs it.
- **Barrels:** none — routes import what they need directly.
- **Tests:** colocated (`*.test.tsx`) next to the file under test.

## Hooks this variant implies

```yaml
deep-import (ST-003): OFF      # no index.ts barrels in this layout
junk-drawer (ST-005): learned  # OFF if the repo already uses utils.ts, else ON
tests (ST-007):       ON       # colocation expected
common rules:         ON       # any / args / naming / error-handling unchanged
```

## `.coding-standards-structure` written when chosen

```yaml
framework: nextjs
variant: route-colocated
where:
  routing:       app/
  feature-code:  app/<segment>/
  route-private: app/<segment>/_<name>/
  shared-ui:     components/
  design-system: components/ui/
  shared-logic:  lib/            # shared utility + infrastructure code, not tied to one feature
naming:
  files: kebab-case
  components: PascalCase, domain-qualified
hooks:
  deep-import: off
  junk-drawer: off               # set by scan: repo already uses utils.ts
  tests-colocated: on
```
