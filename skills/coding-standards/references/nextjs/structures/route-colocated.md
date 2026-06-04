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

## How the rules apply to this variant

This layout is **barrel-less** — routes import what they need directly, no `index.ts` public API. ST-003
deep-import therefore has nothing to enforce, and `block-ts-violations.py` works that out on its own: it
flags `@/a/b/c` only when capability `a/b` exposes a barrel, and here none do. No toggle, no configuration
— the absence of barrels *is* the signal. Every other rule (ST-005 junk-drawer, no-`any`, naming,
arg-count, ST-008 tiers) applies unchanged, as in every layout.

## `.coding-standards-structure` written when chosen

A single `follows:` line — the layout above stays the reference, so it isn't copied into the file. Nothing
else: deep-import is derived from the missing barrels, not declared.

```yaml
follows: route-colocated
```
