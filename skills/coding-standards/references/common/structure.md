# Structure

How to organize code in a project — any language, any framework.

**The framework already set the project's outer folders.** Whatever the framework scaffolds (`app/`,
`components/`, `Controllers/`, `Services/`, and so on), or whatever layout the team picked — follow it
as-is. Don't fight it, don't move it, don't re-document it. The outer shell is not this skill's job.

**This file governs what goes *inside* those folders** — where code actually rots:

- everything dumped flat into one folder,
- one file that does many unrelated jobs,
- a file or folder named `utils` / `helpers` / `common`, which says nothing.

The rule, everywhere:

> Organize the inside by **Business → Feature → Sub-feature → Unit**. One file does one job. When a job
> has interchangeable forms, define one shared interface and one file per form. Shared code rises only to
> the lowest level that covers everything using it.

The codes (ST-001…009) below are labels so reviews and tools can point at a rule.

---

## The four levels

| Level | What it is |
|---|---|
| **Business** | A top-level area of what the product does. |
| **Feature** | One capability within a business. |
| **Sub-feature** | A distinct piece within a feature — created only once **3** related files earn the folder (Rule of Three). |
| **Unit** | One file, one job. The floor. |

Go a level deeper only when there's enough to justify it: one file never gets its own folder; one use
never gets a `shared`.

The shape, in the abstract:

```
<business>/
  <feature>/
    <unit>.<ext>            ← one job each
    <sub-feature>/          ← only once 3 related files earn it
      <unit>.<ext>
      <entry>               ← front door
    <entry>
  <entry>
```

**Where the levels sit depends on the framework's outer shell:**

- The framework lets the top folders be named freely → business folders go at the top
  (`<business>/<feature>/…`).
- The framework dictates the top folders → business and feature folders go *inside* the mandated ones
  (`<mandated-folder>/<business>/<feature>/…`).

Same model, different height. Never fight the framework to lift business folders to the top — apply the
model wherever the folders are yours to name.

---

## ST-001 — Name by meaning, not by kind

A folder or file name states **what it's about** — the part of the product it serves, or the job it does
— never **what technical category it belongs to**.

- Bad — named by kind: `controllers/`, `services/`, `models/`, `repositories/`, `utils/`, `helpers/`, `types/`
- Good — named by meaning: the area of the product, or the job performed (`<verb>-<noun>.<ext>`)

This applies **at whatever level the names are yours to choose**. If the framework hands over a `Services/`
folder, keep it — but inside it, group by area of the product; don't pile everything flat.

**Test:** read the names you created aloud. If they describe the tech stack ("controllers, services,
models"), the inside is filed by kind — wrong. If they describe the product, it's filed by meaning — right.

**Why:** when one part of the product is one folder, changing or deleting it touches one folder. When it's
smeared across kind-named layers, every change touches every layer.

---

## ST-002 — Each folder of substance has one front door

A folder holding more than one file exposes a single entry (`index.ts`, `__init__.py`, a package's
exported names — whatever the language uses) that declares what outsiders may use. Everything else is
private.

```
<feature>/
  <unit-a>.<ext>     ← private
  <unit-b>.<ext>     ← private
  <entry>            ← the front door: the only thing others import
```

The front door is a contract: insides change freely, the door stays stable. Without one, every file is
implicitly public and nothing can be refactored safely.

Single-file folder: callers may import it directly; add the front door when the second file arrives.

---

## ST-003 — Don't reach past the front door

Cross-folder imports go through the destination's front door, never into its internals.

```
// Good
import { thing } from '<folder>'
// Bad
import { thing } from '<folder>/<internal-file>'
```

Reaching in couples the caller to private details, so renaming or moving those details breaks distant code.
Enforce with the project's import linter (the skill catches it at write time; the linter catches it on
every commit).

---

## ST-004 — Don't share until proven; share at the lowest level that covers it

Shared code is the most expensive code — a change to it changes every caller. Earn it:

1. **First use** → write it where it's used.
2. **Second use** → copying is allowed; two small copies beat a wrong abstraction.
3. **Third use** → now extract it.

When extracted, it rises only to the **lowest level that covers everything using it**: used by two features
of one business → it lives at that business's level, not the global shared; used across businesses → only
then the top-level `shared/`.

**Never start in `shared/`** — code written for callers that don't exist yet is the worst kind.

(Exception: stable external infrastructure — a third-party client, a library wrapper — may be shared at two
users, because it won't diverge. Rule of Three guards against sharing *business logic* prematurely, not
against reusing a fixed tool.)

---

## ST-005 — No junk-drawer names

A name that describes nothing collects everything: `utils`, `helpers`, `common`, `misc`. Name a file by
the job it does (`<verb>-<noun>`), so it has exactly one reason to exist.

The same applies to catch-all mega-files — a single top-level `types` or `constants` holding the whole
project. Split them; constants and types live beside the code that owns them.

**`lib` is the one deliberate asymmetry**, and it's intended: a *file* named `lib.ts` / `lib.py` is junk
(it names nothing), and the write-time hook blocks it — but a `lib/` *folder* is allowed. `lib/` is a
conventional home for thin third-party wrappers and shared infrastructure, and two of the bundled layouts
(`route-colocated`, feature-sliced-design's `shared/lib`) depend on it; blocking the folder would fight
those structures and add noise. `utils` / `helpers` / `common` / `misc` get no such pass — they're junk as
both file and folder. (Inside a `lib/` folder, ST-005 still applies to the filenames: name each wrapper by
what it wraps, e.g. `lib/stripe-client.ts`, not `lib/utils.ts`.)

---

## ST-006 — Generic names only in the shared / design-system layer

A name generic enough to mean anything (`Card`, `Modal`, `Button`, `Repository<T>`, `BaseEntity`) says
nothing about the product. Such names belong only in the shared design-system layer. Inside a business or
feature, qualify the name with what it's for (`<domain>Card` rather than `Card`; `<domain>Repository`
rather than `Repository<T>`).

The exact design-system folder name and file suffixes are framework-specific; the framework file gives them.

---

## ST-007 — Tests, types, and styles sit beside what they describe

Anything that exists *because of* a file lives *next to* it.

```
<feature>/
  <unit>.<ext>
  <unit>.test.<ext>      ← beside the file it tests
  <unit>.types.<ext>     ← feature-local types
```

A separate top-level `tests/` tree mirroring the source is forbidden — it drifts from the code and gets
forgotten. (Exception: whole-app end-to-end tests, which belong to no single file, live at the project root.)

---

## ST-008 — One file, one job; grow by splitting, not by piling on

Left unchecked, a file keeps absorbing jobs until it does everything.

**One file = one reason to change.** ST-005 governs a file's *name*; ST-008 governs its *scope*. A file
can be perfectly named and still wrong — if one file parses input, calls an external service, *and* writes
to storage, that's three jobs in one file.

**Split when any of these holds** (check before adding to a file):

- the file already does two or more unrelated things,
- you're about to add a job to a file that already owns a different one,
- it carries **more than 10 behavioral top-level declarations** (functions / classes / methods — things
  that *do* something): that's the hard line for "does many jobs", and a write-time hook blocks on it,
- it has grown past roughly **400 lines** — a softer nudge (a cohesive file can be long), warned but never
  blocked.

These thresholds are fixed by the standard; there is no per-project tuning. A data-only file (a wall of
`const`/`type`/`enum`) carries zero *behavioral* declarations, so length alone never blocks it — the gate
is "how many jobs", not "how big".

**Then** move the new job into its own named file beside the original. Once 3 such siblings share a theme,
promote them to a sub-feature folder with its own front door (Rule of Three). Never create a folder for one
file, or a sub-feature folder for symmetry.

The promotion applies to **any** flat folder, however it grew — siblings created by splits, by extraction,
or by plain accretion all count toward the same three. A split that leaves its folder holding a themed
cluster of 3+ flat files has finished only half the job. Promotion is earned by **cohesion, not folder size** — the flat-sibling count is only a coarse backstop;
3+ units sharing a theme have earned a sub-feature folder even in an otherwise small folder.

**Splitting to beat the counter is not decomposition — it's scatter, and fails ST-008 worse than the
original.** A split is valid only when each file is one genuine job that stands on its own. Two scatter
signals, both violations:

- **Fragments that only make sense together** — pieces carved purely to drop the declaration count,
  unreadable apart. The count improved; cohesion got worse.
- **A copy of a sibling's machinery** — a split reproducing logic another feature already has (see DP-007).
  That multiplies duplication across more files, each individually passing the count.

So the remedy for a decl-count block is a **cohesive** split — or, when the file is genuinely one job the
column-0 proxy miscounts (e.g. a thin feature router that is many small route registrations = one routing
job), a **recorded exemption** in `.coding-standards-ignore` with a one-line reason, logged `accepted` (see
`references/fix-plan.md`). Never a cosmetic scatter.

```
# Before — one file, three jobs
<feature>/
  <feature>.<ext>        ← parses input + calls a service + writes storage
  <entry>

# After — one job per file, same front door
<feature>/
  parse-input.<ext>
  <feature>.<ext>        ← coordinates the steps
  store-record.<ext>
  <entry>
```

**Variants split differently.** When a job has interchangeable forms, don't grow one file with branches —
define **one shared interface plus one file per form**, and select the right one at runtime. A new form is
then one new file; nothing else changes.

```
<feature>/<forms>/
  <form-interface>.<ext>   ← the shared shape every form implements
  <form-a>.<ext>
  <form-b>.<ext>
  <entry>
```

> A write-time hook (`block-god-file.py`) **blocks** when a file has more than 10 behavioral top-level
> declarations — the least-blunt mechanical proxy for "does many jobs". Raw line count and flat-sibling
> count are blunter, so they **warn but never block** (a long cohesive file is legitimate; a flat folder
> may be fine). The judgement past the count — "is this two jobs?", "do these siblings share a theme?" —
> stays with the author and the review, which enforce ST-008 in full regardless of the mechanical line.

---

## ST-009 — Nesting means *part-of*; a nested peer is misfiled

Putting folder B inside folder A asserts B is a *piece of* A and builds on A's front door. The Rule of
Three earns a sub-feature by *count*; ST-009 governs *where* it nests — a cluster is a sub-feature only
of the parent it actually depends on.

A nested folder is a **misfiled peer** when both hold:
- it imports nothing (or only an incidental helper) from the parent's front door, **and**
- it reimplements the parent's own shape — its own registry/service/routes/store mirroring the parent's.

That is a sibling feature wearing a child's folder. File peers as siblings, not nested. Two distinct
features are peers even when they share a name prefix.

**Test:** does the child import from the parent's front door and represent a part the parent delegates
to? Yes → legitimate sub-feature. No, and it duplicates the parent's structure → misfiled peer; move it
out. (Structural companion to DP-007: a nested peer is usually also a parallel-family duplication.)

---

## How framework files build on this

Each `references/<framework>/structure.md` adds only what's specific to that framework: what the front door
*is* in that language, which outer folders the framework forces (so business folders are filed in the right
place), and that framework's own traps. It does not restate the rules above — they load alongside it.

---

## Review checklist

```
Naming & filing
  □ Names describe meaning, not technical kind (no controllers/, services/, utils.ts)
  □ Filed business → feature → sub-feature → unit, inside whatever the framework gave
  □ No junk-drawer names or catch-all mega-files
  □ Generic names (Card, Modal, Repository<T>) only in the shared/design-system layer

File scope (ST-008)
  □ No file does two or more unrelated jobs
  □ Oversized files split into named siblings
  □ Variants split into one-interface + one-file-each, not branches in one file
  □ Sub-feature folders earned by 3+ related files, not made for symmetry
  □ No 3+ themed siblings left flat — once they earn the folder, promote them (same Rule of Three, other direction)
  □ Nested sub-feature folders build on their parent (import its front door, are part-of it) — a nested peer that reimplements the parent is misfiled (ST-009)
  □ Themed 3+ clusters promoted regardless of total folder size (ST-008 promotion by cohesion)

Boundaries & sharing
  □ Each multi-file folder has one front door
  □ No import reaches past a folder's front door
  □ Nothing shared before its third user; shared code sits at the lowest covering level
  □ Tests/types/styles sit beside what they describe
```
