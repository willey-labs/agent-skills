# Structure map (comprehension artifact)

Before the orchestrator checks structure, it **comprehends** it: a top-down model of what the
codebase *is*, expressed in the skill's own hierarchy (`common/structure.md`: Business → Feature →
Sub-feature → Unit). The map is the spec the real tree is diffed against — most ST-* / DP-007 / ST-009
findings are "the real tree doesn't fit this model" deltas, which a per-file pass can never see.

## When it's built
- **Gate first — comprehend only when the structure isn't already recorded, or the user asks for it.**
  No `.coding-standards-structure` yet → comprehend and record the resolved layout. A record exists →
  skip the map and follow the recorded structure (SKILL.md Step 4); don't re-derive or restructure. The
  only thing that forces a (re)build is an explicit "restructure" / "review the structure" / "show me the
  structure tree" request.
- Built in **Review** (orchestrator pipeline) over the whole package/sub-project, gated by the same
  scope threshold as Fix mode (`orchestrator-pipeline.md`). Below the threshold (small diff/PR), skip
  the full map — note that structural cross-feature findings were not run.
- **Persisted** to `<root>/.coding-standards/structure-map.md` (gitignored via the existing
  `.coding-standards/` line; excluded from future reviews like reports/fixes). NOT stored in
  `.coding-standards-structure` — that file stays placement-only (AGENTS.md).
- **Reused** by the Fix pass (it reads the review report + this map) and by the next review unless the
  tree changed materially (regenerate when stale; a one-line staleness note when reused).

## How it's built — grounded, not narrated
Each node MUST be backed by evidence read from the code, never inferred from folder names alone. Read for
two different things — and don't stop at the second:

- **What it is** — the domain the code is about (the Business line, each node's purpose). It lives in
  what's *always* in the repo: the domain nouns in the code's own identifiers (types, classes, functions,
  entities); then the data and content files (constants, enums, config, fixtures, seed data, manifests);
  then any user-facing strings (labels, messages, i18n); then the entry point and what it assembles. A
  README / design notes / package description confirm it when present — but they're optional and they rot,
  so never depend on them. The identifiers and data are the load-bearing source.
- **How it's wired** — placement and boundaries: the folder's front-door exports (`index.*`), a
  representative unit, its cross-folder imports.

Wiring tells you how the pieces connect, never what the product is: reading only exports and imports
yields the *category* ("a web server", "a parser"), not *this* product. For the Business line, read the
identity sources above.

**The Business line is done only when it names what *this* product does.** Test: swap in any competitor in
the same category — if the line still reads true, it's too generic; keep reading the identifiers and data.
The one exception is a project that genuinely *is* its category (a generic date-parsing library really is
"a date parser") — then the category line is correct and complete. The bar is "did you read the names and
data", not "must sound unique".

**The Feature axis is wrong until you've traced a capability against it.** The Business line can be right
and the features under it still just echo the folder names — the most common failure of this whole pass,
because mirroring the existing layout produces a map that passes a glance and trips no error. So before
presenting, run for the feature axis the test the bar above runs for the root: pick one capability and
trace its files across the tree (grep its domain nouns; follow its entry point's imports). If that one
capability's pieces are scattered across 3+ kind-named folders — folders named for a technical layer or
artifact type rather than for what the product does — the map is filed by kind, not by capability; rebuild
it on the capability axis before going further. The tell is a feature list whose names line up one-for-one
with the folder names: that means you read the layout, not the product. This is not optional polish — it is
the step that separates a map of what the code *does* from a relabeling of where the files *sit*.

For large trees the orchestrator may dispatch a comprehension agent per top-level folder (read + return
that folder's node as JSON), then assemble. Keep context lean: read excerpts, not whole files.

## Confirm once (large reviews)
Present the map compactly and confirm it **before any checks run** — a wrong map poisons every downstream
finding. **Lead the confirmation with the Business line and the feature axis, not the folder tree:** both
are likely to be wrong and unlikely to be noticed — the line because it's easy to write too generic, the
axis because a feature list that echoes the folders looks valid at a glance — and a user scanning a folder
tree will rubber-stamp either. Carry the one-capability trace from the Feature-axis test into the question
as evidence the split is derived from what the product does, not from where the files sit. Ask one
`AskUserQuestion` (reuse the Step 4 structure-resolution shape):

> I read this project as: **<Business line>**. Its capabilities are **<feature axis>** — e.g. <one
> capability> is spread across <N files in M folders>, which is why the split follows the capabilities
> rather than the folders they're currently filed under. Is that what this product is, and is that
> Business/Feature/Sub-feature split right?

If the Business line comes back wrong, the map is wrong at the root; if the split just mirrors the folder
names, the axis is wrong. Either way rebuild from the identity sources above (and the capability trace)
before touching any check; do not patch the tree in passing and proceed. Below the scope threshold no map
is built, so there's nothing to confirm — say that cross-feature structural checks were not run.

## Format

```markdown
# Structure map — <sub-project path>  (comprehended <ts>, confirmed <ts|unconfirmed>)

Business: <one line — what *this* product does, in its own terms, not its category (see the Business-line bar above)>

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
