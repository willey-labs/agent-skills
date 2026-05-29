# Next.js — `screaming-architecture`

**Organize by capability, with a fixed internal skeleton per use case.** Top-level folders inside `src/` are business capabilities (nouns); inside each, folders are use cases (verb phrases); inside each use case, files live in fixed technical subfolders. Nothing is global unless three places need it.

This is the skill's **original** Next.js structure — the strict end of the feature-first family, and the most prescriptive entry in this catalog. Best when a team wants one uniform shape everywhere and is willing to enforce it.

## Layout

```
src/
  app/                          # routing — thin; composes use cases, no business logic
    (group)/<segment>/page.tsx
  <capability>/                 # business capability, a NOUN: appointments/, prescriptions/
    <use-case>/                 # a use case, a VERB PHRASE: book-appointment/, cancel-appointment/
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
- **Components:** `PascalCase`, domain-qualified — `AppointmentCard`, not `Card`. Generic names only in `shared/ui/`.
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
deep-import (ST-003): ON       # the index.ts public API is mandatory
junk-drawer (ST-005): ON       # no utils.ts / helpers.ts anywhere
tests (ST-007):       ON
common rules:         ON
```

## `.coding-standards-structure` written when chosen

```yaml
framework: nextjs
variant: screaming-architecture
source: this skill (original structure.md)
where:
  routing:               app/                            # thin
  capability:            src/<capability>/               # noun
  use-case:              src/<capability>/<use-case>/    # verb phrase
  use-case-parts:        [components, hooks, lib, api, schemas]
  use-case-public-api:   src/<capability>/<use-case>/index.ts
  capability-public-api: src/<capability>/index.ts
  shared:                src/shared/                     # ui, lib, hooks, config, types
naming:
  files: kebab-case
  components: PascalCase, domain-qualified
imports:
  rule: "app -> capabilities -> shared"
  cross-capability: via index.ts only
hooks:
  deep-import: on
  junk-drawer: on
  tests-colocated: on
```
