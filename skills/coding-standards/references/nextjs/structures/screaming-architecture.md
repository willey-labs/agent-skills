# Next.js — `screaming-architecture`

**Organize by capability, with a fixed internal skeleton per use case.** Top-level folders inside `src/` are business capabilities (nouns); inside each, folders are use cases (verb phrases); inside each use case, files live in fixed technical subfolders. Nothing is global unless three places need it.

This is the skill's **default** Next.js structure — the strict end of the feature-first family, and the most prescriptive entry in this catalog. Best when a team wants one uniform shape everywhere and is willing to enforce it.

> This variant follows `common/structure.md` for the inside of every folder; everything below is just its outer shape — where the business / feature / use-case folders sit, and the fixed per-use-case skeleton that defines this variant.

## Layout

```
src/
  app/                          # routing — thin; composes use cases, no business logic
    (group)/<segment>/page.tsx
  <capability>/                 # business capability, a NOUN
    <use-case>/                 # a use case, a VERB PHRASE
      components/               # ALL React components for this use case
      hooks/                    # ALL hooks
      lib/                      # ALL pure business logic
      api/                      # ALL server actions / fetches
      schemas/                  # ALL validation schemas
      types.ts                  # use-case types
      index.ts                  # REQUIRED public API
    <capability>.types.ts       # capability-scoped types
    index.ts                    # REQUIRED capability public API
  shared/                       # cross-cutting — 3+ capabilities only (Rule of Three)
    ui/  lib/  hooks/  config/  types/global.ts
```

## Conventions

- **Top level = capabilities (nouns); use cases = verb phrases** — read the folder names aloud as a product spec.
- **Mandatory nesting:** a component MUST live in `components/`, a hook in `hooks/`, logic in `lib/` — never at the use-case root.
- **Components:** `PascalCase`, domain-qualified — `<Domain>Card`, not bare `Card`. Generic names only in `shared/ui/`.
- **Three type scopes:** use-case `types.ts` → capability `<domain>.types.ts` → `shared/types/global.ts`. Promote only when a second user appears.
- **Add a folder when you write its first file** — no empty folders.

## Import rule

```
app  →  capabilities  →  shared        # downward only
```

- Cross-capability imports go through the capability's `index.ts` **only** — no deep imports.
- Enforce with ESLint `import/no-restricted-paths`.

## Hooks this variant implies

```yaml
deep-import (ST-003): ON       # the index.ts public API is mandatory — the only variant-driven toggle (god-file is a separate project-level advisory)
universal rules:      ON       # ST-005 junk-drawer, no-any, naming, arg-count, ST-008 tiers — mandatory, never per-variant
```

## `.coding-standards-structure` written when chosen

Recording the choice is a single `follows:` line — the layout above stays the reference, so it isn't copied into the file. The mandatory `index.ts` public API means `deep-import` stays on (the default) and needs no toggle:

```yaml
follows: screaming-architecture
```
