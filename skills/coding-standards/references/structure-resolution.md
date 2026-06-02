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

## Where the file lives — the framework project root, not the repo root

The hooks find `.coding-standards-structure` by walking up from the edited file to the **nearest**
directory holding a project marker (`package.json`, `go.mod`, `pyproject.toml`, `.git`, `*.csproj`, …) —
see `hooks/_exclusions.py`'s `find_project_root`.

- **Single-project repo** → that's the repo root.
- **Monorepo** → that's the individual sub-project (`apps/web/`, `services/api/`). A Next.js app and a
  Hono service in the same repo resolve to *different* files with *different* structures, each next to
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
- Otherwise it **describes a custom layout** → follow it as written.

Either way: done, no question.

### Case 2 — no file, but the folders match the framework's recommended structure

Use that bundled reference (a catalog variant, or the single `structure.md`). Done — no question, no
file. It's re-recognised from the folders every run, so nothing needs saving.

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

## After the user answers

### Keep current

Scan → draft the layout → user confirms → write `.coding-standards-structure` (the learned custom layout).

A kept layout governs *placement* only — which folder a new file lands in. It does not exempt new code
from any rule: all seven `common/` rules still apply to every file, including ST-008 tier decomposition
(Domain → Feature → Sub-feature → Unit). A custom layout never lets a god-file or a `utils.ts` through, and
a legacy repo full of `utils.ts` is no reason to relax ST-005 — the next edit to such a file is blocked
until it's renamed.

Only three checks are toggleable — one because a layout can genuinely lack the structure it checks for,
two because they are advisories that never block, so relaxing the *reminder* is fine:

- `deep-import: off` — when the layout has no barrels by design (route-colocated, flat Go/Python). ST-003
  has nothing to check without barrels; left on it would flag every import.
- `god-file: off` (or `god-file-max-lines` / `god-file-max-decls`) — the ST-008 size advisory. ST-008
  itself is still enforced when the skill writes and reviews. Defaults: 400 lines / 10 declarations.
- `flat-folder: off` (or `flat-folder-max-files`) — the ST-008 promotion advisory: warns when a new
  source file lands in a folder already holding more than the threshold of flat source units (3+ themed
  siblings have earned a sub-feature folder, Rule of Three). Off for layouts that are flat by design
  (a large idiomatic Go package). Default: 12 files.

These three are the entire `hooks:` block; every other rule is mandatory and not listed there. The hooks read
the toggles via `hooks/_structure.py` — a missing toggle stays on, an unrecognised key is ignored. Example:

```
# .coding-standards-structure
layout: |
  src/<feature>/{ui,model,api}.ts
hooks:
  deep-import: off
  god-file-max-lines: 600
```

### Pick a standard

Use that structure's bundled reference for this run, and write `.coding-standards-structure` with a single
`follows: <framework-or-variant>` line — no custom-layout body.

One exception: if the chosen variant is **barrel-less** (its reference marks `deep-import: OFF`, e.g.
`route-colocated`), add a `deep-import: off` line too — the hook can't infer it from `follows:` alone.

```
# .coding-standards-structure
follows: route-colocated
hooks:
  deep-import: off
```

---

## Messy / custom project, first run

When the layout is messy and the user keeps it, the drafted file may be silent on where a *new* artifact
belongs. The new file then falls back to `common/structure.md` (ST-*) + the framework default — for the
new file only, with the placement noted.

- **Write task:** Worker 1 never reorganizes existing misplaced files (no scope creep). It places the
  task's new files cleanly; the orchestrator offers a separate migration pass.
- **Review task:** existing misplacement *is* reported — but only for files in the review scope, never
  the whole repo.

---

## How this feeds the rest of the run

The resolved structure replaces `references/<framework>/structure.md` in SKILL.md's Step 7b load list. The seven
`common/` files always load and apply unchanged, whatever structure is chosen. In the orchestrator
pipeline the resolved structure is passed to Worker 1 as its `STRUCTURE` input (see
`orchestrator-pipeline.md`) — Worker 1 checks placement against the resolved layout, never a default it
picked on its own.
