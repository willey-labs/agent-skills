# Structure map (comprehension artifact)

Before the orchestrator checks structure, it **comprehends** it: a top-down model of what the
codebase *is*, expressed in the skill's own hierarchy (`common/structure.md`: Business → Feature →
Sub-feature → Unit). The map is the spec the real tree is diffed against — most ST-* / DP-007 / ST-009
findings are "the real tree doesn't fit this model" deltas, which a per-file pass can never see.

## When it's built
- Built in **Review** (orchestrator pipeline) over the whole package/sub-project, gated by the same
  scope threshold as Fix mode (`orchestrator-pipeline.md`). Below the threshold (small diff/PR), skip
  the full map — note that structural cross-feature findings were not run.
- **Persisted** to `<root>/.coding-standards/structure-map.md` (gitignored via the existing
  `.coding-standards/` line; excluded from future reviews like reports/fixes). NOT stored in
  `.coding-standards-structure` — that file stays placement-only (AGENTS.md).
- **Reused** by the Fix pass (it reads the review report + this map) and by the next review unless the
  tree changed materially (regenerate when stale; a one-line staleness note when reused).

## How it's built — grounded, not narrated
Each node MUST be backed by evidence read from the code, never inferred from folder names alone:
- the folder's front-door exports (`index.*`), a representative unit, and its cross-folder imports.
- For large trees the orchestrator may dispatch a comprehension agent per top-level folder (read +
  return that folder's node as JSON), then assemble. Keep context lean: read excerpts, not whole files.

## Confirm once (large reviews)
Present the map compactly and ask the user **one** question: "is this the intended Business/Feature/
Sub-feature structure?" (reuse the `AskUserQuestion` shape from Step 4 structure-resolution). Confirm
*before* checks run, so a wrong map is caught before it cascades. A wrong map poisons every downstream
check. Below the scope threshold, skip the question.

## Format

```markdown
# Structure map — <sub-project path>  (comprehended <ts>, confirmed <ts|unconfirmed>)

Business: <one line — what the product/sub-project does>

## Features
- <feature-folder>/ — <what it's about>  [product | core/infra | shell]
  - sub: <sub-feature folders, or "none">
  - units: <key units + one-word job>
  - front door: <what index exports>  · depends on: <other features it imports from>

## Relationships & deltas (candidate structural findings)
- <rule code>: <the mismatch between the real tree and the model> — <evidence file:line> — <fix shape>
```

A node with sub-features lists them; a delta names the rule it will become (ST-001/004/008/009, DP-007).
The deltas are *candidate* findings — Worker 1 confirms them against the loaded rules.

## Worked example — abstract skeleton (illustrative only)

This is a **name-free skeleton, not a real project**. Every folder name is a structural placeholder
(`engine/`, `shared/`, `feature-a/`, `resource/`) that names a *role*, never a domain — there is no
"right answer" to copy. Do NOT pattern-match a real codebase onto it; build your map fresh from the
tree in front of you. It exists only to show the *shape* of a map and the kinds of deltas a
comprehension pass surfaces, in terms any project can read.

```markdown
# Structure map — <sub-project path>  (comprehended <ts>, unconfirmed)

Business: <one line — what this sub-project actually does, in the project's own terms>

## Features
- engine/ — the core processing unit the rest of the system drives.  [core/infra]
  - sub: input/, parsing/, state/
  - units: driver.ts (a state machine — cohesive, NOT a god class), frame-parser.ts, lifecycle.ts, ...
  - front door: engine/index.ts · depends on: shared (errors)
- shared/ — the shell + the one adapter every request-style feature should build on.  [shell]
  - sub: protocol/ (the request→response pump + body/usage shapers, error-mapper) ← the shared home
    the entrypoint features below should build on
- feature-a/ — public entrypoint A.  sub: variant-x/ (+ a flat variant-y handler — asymmetric)
- feature-b/ — public entrypoint B.  sub: variant-x/, variant-y/
- feature-c/ — public entrypoint C.
- resource/ — single-instance resource (one long-lived record)
- pooled-resource/ — pooled variant  [PEER of resource — currently MISNESTED under resource/]
- assets/, observability/ — blob store, request-log store

## Relationships & deltas (candidate structural findings)
- DP-007 / ST-004: feature-a, feature-b, pooled-resource each hand-roll the same request-drive +
  response pump + body/usage shaper; the shared home shared/protocol/ exists — feature-a uses it, the
  other two bypass it (feature-b/variant-x/handler.ts, pooled-resource/pooled-resource.stream.ts).
  Fix: route all three through shared/protocol/.
- ST-009: resource/pooled-resource/ is a peer of resource/ (own store/service/routes; shares only a
  resource-access helper) — nested as a child. Fix: lift it to a sibling; put the shared helper in a
  front-doored home both reach.
- ST-001: one feature is split across two folders — feature-c/feature-c.routes.ts imports its Store
  from ../feature-c-store/index.js (routes in one folder, store in another). Fix: one feature, one folder.
- ST-008 (promotion, cohesion not count): feature-b/ holds a flat 5-file step-* cluster (8-file folder,
  so the 12-decl advisory never fires) → feature-b/steps/. engine/ holds a 3-file boot-* cluster (incl.
  one ~470-line unit — check DP-001) → engine/boot/.
- NM (stutter): feature-a/feature-a-*.ts, feature-b/feature-b-*.ts repeat the folder name in the file name.
```
