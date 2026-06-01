# Vanilla JS / TS — Structure

## Builds on `common/structure.md`

Plain JavaScript/TypeScript (Node scripts, browser-only apps, libraries, CLIs) has no framework shell, so
the universal rules in `common/structure.md` *are* the architecture — there's nothing on top to constrain
folder layout. Read that first; this file adds only the JS/TS specifics.

## Outer shell

The top folders are yours to name, so business folders go at the top, under a `src/` root:

```
src/
  <entry>                  ← app entry point (browser bootstrap / CLI start), or the library's public entry
  <business>/
    <feature>/
      <unit>.ts            ← one job each
      index.ts             ← front door
    index.ts
```

Decompose the inside business → feature → sub-feature → unit per `common/structure.md`. Nothing here is
special; vanilla JS/TS is the closest case to the universal model.

## Naming

- **Classes / types** — `PascalCase.ts` (`HttpClient.ts`, `RateLimiter.ts`).
- **Function modules** — `verb-kebab-case.ts` (`parse-date.ts`, `slugify.ts`).
- **Folders** — `kebab-case/`.
- **Front door** — always `index.ts`.

There's no community-wide convention here (unlike React or Laravel), so pick one per project and hold to
it; the table above is the skill's default.

## Front door

Each folder of substance exposes a single `index.ts` that re-exports its public API; everything else stays
private. Cross-folder imports go through that `index.ts`, never into internal files (`common/structure.md`,
ST-002/003).

## JS/TS specifics

- **No mega-barrel at the package root.** Barrels are per-folder, not per-app. A single root
  `index.ts` that does `export * from './<every-folder>'` forces every consumer to pull in the whole
  package and defeats tree-shaking, because the bundler can't statically prune what a wildcard re-export
  hides. For an app this is just dead weight; for a published library it bloats every downstream bundle.
  Expose deliberate entry points instead — name the symbols, one narrow public surface:

  ```ts
  // ❌ src/index.ts — kills tree-shaking
  export * from './<business-a>'
  export * from './<business-b>'

  // ✅ src/index.ts — explicit, narrow surface
  export { <Name> } from './<business-a>'
  export { <Name> } from './<business-b>'
  ```
