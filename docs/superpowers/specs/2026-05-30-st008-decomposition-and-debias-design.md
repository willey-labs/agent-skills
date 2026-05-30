# Design: ST-008 (tier decomposition) + DP-002 trigger + de-bias `common/structure.md`

**Date:** 2026-05-30
**Skill:** `coding-standards`
**Status:** Approved design — pending implementation plan

---

## Problem

When the skill writes code, it dumps multiple responsibilities into one file (e.g. a 2000-line
`runner.ts` mixing a state machine, regex parsers, file I/O, and rate-limit parsing). The file is
*well-named*, so it passes every existing check, yet it is a God Module.

Root causes:

1. **No structural rule against god-files.** `ST-005` bans junk-drawer *names* (`utils.ts`); it does
   not catch a well-named file that accreted many responsibilities. `FN-001` caps *function* length,
   not *file* length. `DP-001` (SRP) is stated as a principle but never operationalized into a
   "split this file" rule with a detectable trigger.
2. **Judgement rules get skipped in fast/single-agent mode.** The decomposition judgement lives in
   Worker 1 (Structure), which only runs in the orchestrator/"Multiple agents" path. In single-agent
   or quick-edit mode there is no write-time signal, so the file keeps growing.
3. **`common/structure.md` is not actually common.** It bakes framework specifics (a Laravel
   exception in ST-001, React/UI examples in ST-006, TS file-suffixes in ST-007) into the file that
   claims to be language-agnostic. A new common rule would inherit that bias.

The SOLID behavioral half is **already covered** — `DP-001`–`DP-005` are SRP/OCP/LSP/ISP/DIP, and
`DP-002` already prescribes "extract an interface for variants; new variants implement it without
touching the old ones." That is the JSON-handler / terminal-handler Strategy case. We are **not**
adding SOLID; we are making it *followable*.

---

## Design principle: a rule is only followed if it is operational

An agent skips a vague principle and obeys an operational rule. Every rule we add or touch must have:

1. **A detectable trigger** — a concrete signal the agent can check against the code in front of it.
2. **A decision procedure** — what to do when the trigger fires (imperative, not philosophical).
3. **A worked before→after** — generic, language-neutral.
4. **Enforcement wiring** — loaded automatically, owned by a worker, on the review checklist, and
   surfaced at write time by a hook.

---

## The four tiers (vocabulary ST-008 introduces)

| Tier | Official name(s) | What it is | Naming rule |
|---|---|---|---|
| 1 | Business Domain / Bounded Context / Capability | A top-level area of *what the product does* | A business noun (`billing`, `identity`), never a tech layer |
| 2 | Feature / Feature Module / Vertical Slice | A cohesive capability inside the domain | A sub-capability noun, on a consistent axis with siblings |
| 3 | Sub-feature / Component / Concern | A distinct piece inside a feature | Named by what it does |
| 4 | Unit / Module file | One responsibility, one file (SRP) | A verb/role; drops context the folder already gives |

Governing rules that already exist and are reused: ST-001 (tier 1 = business), ST-002 (folder =
module with one public `index`), ST-003 (no deep imports), ST-004 (Rule of Three — folders are
earned, never created for a single file), ST-005 (name by what it does), ST-006 (generic names only
where a layer qualifies them), NM-* (a file name drops the context its folder already provides).

---

## Part 1 — New rule `ST-008` (structure: tiers + no god-files)

Added to `references/common/structure.md`, written to the de-biased standard (Part 4).

> **ST-008 — One file, one responsibility; grow folders by tier, not by accretion**
>
> Source is organized in four tiers: **Domain → Feature → Sub-feature → Unit**. A *unit* (one file)
> has one reason to change. When a unit accretes a second responsibility, split it into a sibling
> unit. When a feature's units cluster into groups, promote the group to a sub-feature folder with
> its own `index`.
>
> **The smell:** a well-named file that keeps growing — it passes ST-005 (the name is fine) but does
> several things.
>
> **Detectable trigger (checked before every write):**
> - the file exceeds the project threshold (default ~400 lines / ~10 top-level declarations), **or**
> - the file holds 2+ unrelated responsibility clusters (e.g. a state machine *and* regex parsers
>   *and* file I/O), **or**
> - you are about to *add* a concern to a file that already owns a different one.
>
> **Then:** extract the new concern into a named sibling unit. If three siblings now share a theme,
> introduce a sub-feature folder (Rule of Three, ST-004). Never create a folder for a single file.
>
> **Tier-3 appears only when earned:** if a feature has a handful of flat units, stop at Tier 2.
> Forcing a sub-feature folder there is over-engineering (DP-006 KISS).

Worked before→after (language-neutral): a `<feature>` module doing parse + orchestrate + persist
splits into `parser` / `<feature>` (orchestrator) / `store`, each a sibling unit behind the
feature's `index`.

---

## Part 2 — Make `DP-002` followable (add the Strategy trigger)

`DP-002` (OCP) is correct but has no trigger an agent can catch itself violating. Append:

> **Detectable trigger:** you have written 2+ branches switching on a `type` / `kind` / `mode`
> string, **or** 2+ sibling types named `XHandler` / `XStrategy` / `XProvider`. → That is a Strategy.
> Define one abstraction; each variant implements it (DP-002 / LSP / DIP); the caller depends on the
> abstraction; adding a variant adds a file and edits nothing (OCP). If variants do not all share
> every method, split into capability/role interfaces (ISP — the "can fly" case).

Folder shape for a feature with multiple strategies (reused in the worked example):

```
<feature>/
  handler.ts          ← the abstraction (interface / contract)   [DIP target]
  json-handler.ts     ← strategy 1                                [LSP, OCP]
  terminal-handler.ts ← strategy 2
  stream-handler.ts   ← strategy 3 (added later, nothing else changes)
  index.ts            ← exports the abstraction + a factory/registry
```

---

## Part 3 — Enforcement wiring (why an agent will actually obey)

| Mechanism | Change | Effect |
|---|---|---|
| Auto-load | `ST-008` lives in `common/structure.md` | Loaded on every task (SKILL.md Step 2) |
| Worker 1 brief | add `ST-008` to `owns_rules` + a decomposition decision-procedure | Thorough/review mode enforces it structurally |
| Review checklist | add the god-file + Strategy checks to `common/structure.md`'s checklist and the Review section | Review mode reports with file:line |
| **Soft-warning hook** `warn-god-file.py` | new PreToolUse hook: exit **0** + stderr warning when a non-test/non-schema source file crosses the threshold | **Fires in single-agent/fast mode**, where the judgement passes are skipped — this is the fix for the original complaint |
| `.coding-standards-structure` | add tier definitions + tunable threshold/exemptions (`st-008: { maxLines, maxDecls, off }`) | Per-project tuning; raise the limit or exempt schema files |

### Why the hook warns rather than blocks

A raw line/declaration count has a false-positive rate well above the repo's ~1% hard-block
threshold (legitimately large test files, schema/DTO files, lookup tables). Per `AGENTS.md`
("a regex pattern with a known false-positive rate above ~1% does not belong as a hard block"),
this hook **exits 0 with a stderr warning** — it never blocks. It nudges on the exact write path
that currently skips judgement, without fighting legitimate large files.

### `warn-god-file.py` contract

- Input: standard PreToolUse JSON on stdin (`tool_name`, `tool_input.file_path`,
  `tool_input.content`).
- Skips excluded paths via the shared `hooks/_exclusions.py` `is_excluded_path()`.
- Skips test/schema files by language-agnostic patterns: `*.test.*`, `*.spec.*`, `*_test.go`,
  `test_*.py`, `*Test.java`, `*.schema.*`, `*-schemas.*`, etc.
- Reads threshold/exemptions from `.coding-standards-structure` via `hooks/_structure.py`
  (default ~400 lines / ~10 top-level declarations; `off` disables).
- Emits `ST-008: <file> has <n> lines / <m> top-level declarations — likely more than one
  responsibility. Consider splitting into named sibling units (see references/common/structure.md#st-008).`
- **Always exits 0.** Stdlib only.
- Registered by `bootstrap.py` alongside the existing `block-*.py` hooks.

---

## Part 4 — De-bias `common/structure.md`

The file claims language-neutrality but contains framework specifics. A new common rule must not
inherit that. Fixes:

| Location | The bias | Fix |
|---|---|---|
| ST-001 (~line 23) | The Laravel exception sits *inside* the common file | Move the carve-out to `references/laravel/structure.md`. Common states the principle + "frameworks may carve exceptions — see their file" |
| ST-006 (~lines 130–153) | All React/UI: `.tsx`, `Card`/`Modal`/`Button`, "design-system layer", `shared/ui/`, `components/ui/` | Keep the principle (generic names only at a shared layer — applies to types too). Move the UI worked example to `nextjs` / `react-native` / `vue-nuxt` structure files |
| ST-007 (examples) | TS/React file suffixes (`.types.ts`, `.styles.ts`, `.stories.tsx`) | State co-location neutrally; show 2–3 languages; push framework suffixes to framework files |

ST-003's multi-language linter list and ST-005's multi-language examples are already correct and are
the model. The C# structure file is the honesty template for when a framework idiom legitimately
differs.

**De-biasing principle (stated once in the file):** the common file holds the **language-neutral
principle + a multi-language example**; every framework-specific carve-out lives in
`<framework>/structure.md` under "How framework files extend this." A framework file may *name* an
exception — the common file may never *contain* one.

When the Laravel/React/TS specifics move out, confirm the receiving framework files
(`laravel`, `nextjs`, `react-native`, `vue-nuxt`) state the exception explicitly so no coverage is
lost.

---

## Files touched

- `references/common/structure.md` — add ST-008; de-bias ST-001/ST-006/ST-007; update the review
  checklist.
- `references/common/code-principles.md` — add the Strategy trigger to DP-002.
- `references/laravel/structure.md` — receive the ST-001 Laravel exception.
- `references/nextjs/structure.md`, `references/react-native/structure.md`,
  `references/vue-nuxt/structure.md` — receive the ST-006 UI example.
- `hooks/warn-god-file.py` — new soft-warning hook (stdlib only).
- `hooks/_structure.py` — read `st-008` threshold/exemptions.
- `hooks/review-files.py` — include the new hook in the review linter pass (as a warning, not a
  must-fix).
- `hooks/README.md` — document the new hook + coverage table.
- `bootstrap.py` — register `warn-god-file.py`.
- `workers/worker-1-structure.md` — add ST-008 to `owns_rules` + decision procedure.
- `SKILL.md` — reference ST-008 where structure rules are summarized; note the soft-warning hook is
  advisory.
- `.coding-standards-structure` template (seeded by bootstrap) — document the `st-008` block.

## Out of scope

- Refactoring any consumer project (e.g. `claude-tui`). The skill change is the deliverable; applying
  it to a project is separate work.
- Hard-blocking on file size (deliberately rejected — false-positive rate too high).
- New SOLID rules (already covered by DP-001–DP-005).

## Acceptance

- `ST-008` exists in `common/structure.md` with trigger + decision procedure + worked example, and
  is referenced by the review checklist and Worker 1.
- `DP-002` has the Strategy trigger.
- `warn-god-file.py` warns (exit 0 + stderr) on an over-threshold non-test/non-schema file, is
  silent on excluded/test/schema files, reads `.coding-standards-structure`, and is registered by
  bootstrap.
- No framework-specific carve-out remains inside `common/structure.md`; each moved exception is
  restated in its framework file.
- The hook test matrix and the bootstrap 6-test matrix in `AGENTS.md` still pass.
