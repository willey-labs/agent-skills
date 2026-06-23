# Structure resolution — full mechanics

Step 4 of `SKILL.md` resolves the **folder layout** a project follows. The body of SKILL.md
carries the decision skeleton; this file carries the details you only need when you actually hit
each branch.

> **This is about the outer shell only** — where the top folders sit. The structure you resolve here
> decides *placement*; the inside of every folder still follows `common/structure.md` (business → feature
> → sub-feature → unit), the same whichever shell a project uses. Resolving the shell is the cheap part;
> the inner decomposition is the work.

Each framework offers a **catalog** of ready-made structures under `references/<framework>/structures/`
(or a single `references/<framework>/structure.md` when it has no catalog yet). A project either
follows one of those or keeps its own custom layout.

- **Folders already match a standard** → re-recognised from the folders every run. No question, no file.
- **Custom layout** → asked once; the choice is saved to a `.coding-standards-structure` file so the
  question never returns.

> Catalog status: **Next.js** ships `route-colocated`, `feature-first`, `screaming-architecture`,
> `feature-sliced-design`. Other frameworks fall back to their single `structure.md` until a catalog exists.

---

## The file records structure only — never rule config

`.coding-standards-structure` answers one question: *what folder structure does this project use?* It
records placement, in up to two parts:

- a **`follows: <framework-or-variant>`** line — which catalog standard the project adheres to, and
- a **`layout:` body** — the project's **actual solved structure tree**: the full feature / sub-feature
  skeleton, so later runs follow *this tree*, not a generic convention that could be re-derived into a
  different shape.

A project may carry **both** — `follows:` names the rulebook, `layout:` pins the concrete tree. It does
**not** carry comments, a `hooks:` block, or any rule toggle. Every coding-standards rule is always
enforced; a project chooses where its files live, never which rules apply or how strict they are. The
`block-structure-file-violations.py` hook blocks any write that tries to slip a comment, a `hooks:` block,
or a legacy toggle (`deep-import`, `god-file*`, `flat-folder*`) into the file.

Checks that *used* to be (or look like they should be) toggled here are derived, not configured:

- **ST-003 deep-import** is decided per import: `@/a/b/c` is flagged only when capability `a/b` actually
  exposes an index barrel (a public API to reach past). A barrel-less layout — `route-colocated`, a flat
  Go/Python package — has no barrel, so nothing is flagged. No `deep-import: off` line is needed or
  allowed; `block-ts-violations.py` works it out from the folder.
- **ST-008 god-file / flat-folder** run at the standard's fixed thresholds on every project. They are not
  silenced or retuned per project — `block-god-file.py` blocks on too many behavioral declarations and
  advises on raw size / flat folders, the same everywhere.
- **ST-005 folder allowance** is read from the `follows:` standard, not a toggle: when a project follows a
  catalog variant that *publishes* a folder that would otherwise read as junk (bulletproof-react's
  `utils/` under `feature-first` and `route-colocated`), `block-junk-paths.py` allows that exact folder
  name. Derived from the adopted standard — the user cannot whitelist arbitrary folders here. The allowance
  is folder-only: junk *filenames* (`utils.ts`) and the `src/<name>` mega-file ban are never relaxed, and
  `helpers/` / `common/` / `misc/` are never sanctioned by any variant.

---

## Where the file lives — the framework project root, not the repo root

The hooks find `.coding-standards-structure` by walking up from the edited file to the **nearest**
directory holding a project marker (`package.json`, `go.mod`, `pyproject.toml`, `.git`, `*.csproj`, …) —
see `hooks/_exclusions.py`'s `find_project_root`.

- **Single-project repo** → that's the repo root.
- **Monorepo** → that's the individual sub-project (`apps/web/`, `services/api/`). A Next.js app and a
  Go service in the same repo resolve to *different* files with *different* structures, each next to
  its own `package.json` / `go.mod`.

Always write the file where the hook reads it — the sub-project root. A file dropped at the monorepo
root is invisible: each sub-project stops at its own nearer marker.

---

## The decision, in full

### Case 1 — a `.coding-standards-structure` file exists at the framework project root

Read it; it records the resolved choice:

- A **`follows: <framework-or-variant>`** line → the project adopted that standard as its target. Load
  that standard's reference and apply it. If the folders haven't migrated yet, flag the gaps as drift
  *toward* the target rather than re-asking.
- Otherwise it **describes a custom layout** (`layout:` body) → follow it as written.

Either way: no question. But before trusting it, **self-heal a non-canonical file** (below).

### Case 2 — no file, but the folders match the framework's recommended structure

Use that bundled reference (a catalog variant, or the single `structure.md`) — no question. But **record
it**: comprehend the tree once and write `.coding-standards-structure` with the `follows: <standard>` line
**plus** the full `layout:` tree (the actual solved structure). Recording even a clean standard match is
what lets later runs skip re-comprehension (SKILL.md Step 4: a record exists → follow it, don't re-open).
A matching project left fileless would re-comprehend on every run — so don't leave it fileless.

### Case 3 — no file, and the layout is custom → ask once

Use `AskUserQuestion`. The question names the detected framework and states the finding; every option
carries a folder-tree `preview`. Order recommended first, "keep current" last (tag the lead option
`(Recommended)`):

> Detected **{framework}**. Your folder layout doesn't match a standard {framework} pattern. Switch to a
> recommended structure, or keep your current one?

**First, count the structures the framework actually ships** — entries under
`references/<framework>/structures/`, or its single `structure.md`. That count decides the question's
shape. No framework is special-cased; the count is just data.

**Framework ships more than one structure** — up to four options:

1. **{closest variant} (Recommended)** — the catalog variant nearest the project's actual layout (fall
   back to the canonical default if none is close). Its **Layout** tree is the `preview`.
2. **…the two most relevant other variants** — `preview` is each one's **Layout** tree.
3. **Keep current** (last) — keep the project's own layout, learned and written to the file.

`AskUserQuestion` allows 4 options + an auto "Other"; route any remaining variants through "Other".

**Framework ships exactly one structure** — same question, two options:

1. **Follow the {framework} default (Recommended)** — `references/<framework>/structure.md`.
2. **Keep current** — keep the project's own layout.

Don't skip the question just because there's only one structure: a project matching neither the one
bundled structure nor anything else still chooses between *adopt the default* and *keep + record current*.

---

## Self-heal — normalise a non-canonical file on read

A `.coding-standards-structure` written by an older skill version (or hand-edited) may carry comments, a
`hooks:` block, or toggle keys. When Case 1 reads such a file, **normalise it in place** before using it:

1. Keep the `follows:` line, or the `layout:` body — whichever the file records.
2. Drop everything else: every comment line, the whole `hooks:` block, every toggle key (`deep-import`,
   `god-file*`, `flat-folder*`). A legacy `deep-import: off` is simply discarded — the hook derives
   barrel-less-ness itself, so nothing is lost.
3. Write the cleaned file back (a clean rewrite always passes
   `block-structure-file-violations.py`), and **report it** — e.g. `normalized
   .coding-standards-structure (removed legacy comments / rule toggles)`. Never silent.

This is how a project that predates the toggle removal gets cleaned: not by a manual sweep, but the next
time the skill resolves that project's structure. The resolved choice (the `follows:` target or the
custom layout) is unchanged — only the cruft is gone.

---

## After the user answers

### Keep current

Scan → draft the layout → user confirms → write `.coding-standards-structure` with the **full solved tree**
as a `layout:` body (plus a `follows:` line if it also adheres to a standard). Record the actual feature /
sub-feature skeleton, not just a pattern — later runs follow *this* tree. **No `hooks:` block, no
comments** — the validator blocks those, and there's nothing to configure: a kept layout governs
*placement* only.

A kept layout does not exempt new code from any rule. All seven `common/` rules still apply to every
file, including ST-008 tier decomposition (Domain → Feature → Sub-feature → Unit) and ST-005 (no
`utils.ts`). A custom layout never lets a god-file or a junk-drawer name through, and a legacy repo full
of `utils.ts` is no reason to relax ST-005 — the next edit to such a file is blocked until it's renamed.

```
# the file records the actual solved tree (placement only)
layout: |
  src/
    <feature>/         one capability per top folder
      <unit>.ts
      <sub-feature>/   once 3+ related files earn it
      index.ts
```

### Pick a standard

Use that structure's bundled reference for this run, and write `.coding-standards-structure` with the
`follows: <framework-or-variant>` line **plus** the full `layout:` tree (the actual solved structure):

```
follows: route-colocated
layout: |
  src/
    <feature>/
      <unit>.ts
      index.ts
```

A barrel-less variant (e.g. `route-colocated`) still needs no toggle: deep-import is derived from the
absence of barrels, not declared.

### When the record is written — and rewritten

Write it the first time the structure is resolved (Case 2 / 3) or whenever the user confirms a restructure
— that's the **target**. After a **Fix** run applies the structural moves, rewrite the `layout:` to the
**achieved** tree, so the record always matches what's on disk (`orchestrator-pipeline.md`, Fix mode). If
Fix deferred some moves, the rewritten `layout:` mirrors what's actually there and the report tracks the
open breaches — the record never claims a structure that isn't on disk. Fix never hand-edits the file; it
rewrites the layout to mirror the tree it produced.

---

## Messy / custom project, first run

When the layout is messy and the user keeps it, the drafted `layout:` body may be silent on where a *new*
artifact belongs. The new file then falls back to `common/structure.md` (ST-*) + the framework default —
for the new file only, with the placement noted.

- **Write task:** Worker 1 never reorganizes existing misplaced files (no scope creep). It places the
  task's new files cleanly; the orchestrator offers a separate migration pass.
- **Review task:** existing misplacement *is* reported — but only for files in the review scope, never
  the whole repo.

---

## How this feeds the rest of the run

The resolved structure replaces `references/<framework>/structure.md` in SKILL.md's Step 7b load list. The
seven `common/` files always load and apply unchanged, whatever structure is chosen. In the orchestrator
pipeline the resolved structure is passed to Worker 1 as its `STRUCTURE` input (see
`orchestrator-pipeline.md`) — Worker 1 checks placement against the resolved layout, never a default it
picked on its own. No rule is enabled or disabled by the structure: placement is the only thing that
varies.
