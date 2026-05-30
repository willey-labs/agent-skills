# Design: Fix mode — apply review findings at scale via per-file fan-out

**Date:** 2026-05-30
**Skill:** `coding-standards`
**Status:** Approved design — pending implementation plan
**Companion to:** `2026-05-30-st008-decomposition-and-debias-design.md` (ship ST-008 first, then this)

---

## Problem

When asked to fix the findings from a review across many files, the skill does only **partial**
fixes. Observed on `claude-tui` (`test-coding-standards.txt`): a review produced **97 findings across
63 files**; in the fix step the single agent tried to hold all file contents in its context, hit the
limit, reasoned *"dispatching all three workers with full file contents would exceed context limits,
let me take a pragmatic approach,"* then fixed a handful of files and stopped. Re-prompting only
produced more partial passes.

Root cause: the skill has **Write mode** and **Review mode** but **no "apply the findings" mode**,
and no **fan-out** shape. The existing orchestrator pipeline (Worker 1→2→3, sequential) is built for
one bounded scope, with file contents flowing through the orchestrator's context. At 63 files that
model exceeds the budget, so the agent abandons the pipeline and improvises into a partial result.

The fix the user identified: **when the scope is too large for one context, that is exactly when to
fan out to multiple agents — one per file — not give up.**

---

## Design principles

1. **One file per agent.** Each fan-out agent receives **only one file's current content + the
   findings scoped to that file** — never the whole file set. Large scope *triggers* fan-out instead
   of triggering surrender. Context per agent stays bounded regardless of total scope.
2. **Completeness ledger.** Every finding is tracked to `fixed` or `deferred(reason)`. "Fix
   everything" becomes auditable; silent partial completion is impossible. This directly answers the
   "only fixes half" complaint.
3. **Structural-vs-file-local partition.** Cross-file fixes have ordering dependencies and cannot be
   blindly parallelized; file-local fixes are independent and fan out cleanly.
4. **The orchestrator still owns all writes.** Fan-out agents emit fixed file content as JSON; the
   orchestrator writes each file so the existing hooks fire once per file (same invariant as Write
   mode).

---

## The Fix pipeline

Fix mode is a new `MODE: fix` execution shape in `orchestrator-pipeline.md`, plus a new entry in the
SKILL.md mode routing. It runs **only as the orchestrator pipeline** (it is inherently multi-file);
if the `Agent` tool is unavailable, it degrades to a sequential, ledger-tracked single-context pass
that processes files in batches and reports what remains.

```
Findings (from a .coding-standards/reviews/<ts>.md report, or an in-session review)
  │
  ├─ 1. Build the completeness ledger — one row per finding: {file, line, rule, severity, status}
  │      status starts `pending`.
  │
  ├─ 2. Partition findings:
  │       • STRUCTURAL / cross-file  → ST-002 (barrels), ST-003 (deep imports), ST-008 (splits),
  │                                    file moves/renames. Ordering matters.
  │       • FILE-LOCAL               → FN-*, NM-*, EH-*, FMT-*, OD-003. Independent per file.
  │
  ├─ 3. PHASE A — structural, coordinated (sequential within the phase):
  │       a. Create/extend barrels (index files) first.
  │       b. Rewrite deep imports to the new public entries.
  │       c. Apply ST-008 splits (new sibling files + move declarations).
  │       Each write goes through the orchestrator → hooks fire. Mark those findings fixed/deferred.
  │       (Phase A may itself fan out for independent barrels, but import rewrites that depend on a
  │        barrel run after that barrel exists.)
  │
  ├─ 4. PHASE B — file-local, fan-out (parallel, one agent per file, batched to the concurrency cap):
  │       For each file with remaining file-local findings:
  │         dispatch a fix-agent with INPUT = { that file's current content, its findings only,
  │                                             FRAMEWORK, STRUCTURE }.
  │         The agent returns { path, fixed_content, fixed[], deferred[{finding, reason}] } — JSON.
  │       The orchestrator writes each returned file (hooks fire per file) and updates the ledger.
  │
  ├─ 5. VERIFY — re-run hooks/review-files.py over every changed file. Any finding that should have
  │       been fixed but still trips the linter flips back to `pending` for one more targeted pass
  │       (max 2 passes per file; then `deferred(reason="re-fix failed")`).
  │
  └─ 6. REPORT against the ledger: "N of M findings fixed across K files; D deferred." List every
        deferred finding with its reason. NEVER stop silently — an incomplete run states exactly
        what remains and why.
```

### Why a per-file fan-out agent, not the 3-worker pipeline

The Write-mode pipeline (Worker 1→2→3) is for *authoring* one scope, where structure→quality→failure
must flow in sequence on the same code. Fixing existing files from a finding list is different:
the findings are already categorized, and the unit of independent work is **a file**, not a rule
domain. So Fix mode fans out by file. Each fix-agent applies *all* rule domains to *its one file*,
guided by that file's findings — it is a focused, context-bounded specialist for one file.

### Fan-out agent brief (new `workers/fix-agent.md`)

- **Owns:** applying a given list of findings to a single file.
- **Input:** `FILE_PATH`, `CURRENT_CONTENT`, `FINDINGS` (the subset for this file, each with rule +
  line + concrete fix), `FRAMEWORK`, `STRUCTURE`.
- **Must not:** touch any other file; introduce findings not in its list (no scope creep); leave a
  finding silently unaddressed — anything it can't fix goes in `deferred` with a reason.
- **Output (JSON only):** `{ "path", "fixed_content", "fixed": [finding-ids], "deferred": [{ "id",
  "reason" }] }`.
- Never calls `Write`/`Edit` (orchestrator writes; hooks fire there).

---

## Triggering Fix mode

- **SKILL.md mode routing:** add a Fix path. It triggers when the user says "fix the findings",
  "apply the review", "fix everything from the review", or fixes are requested right after a review.
- **Step 1.5 run-mode:** Fix mode is always the orchestrator pipeline (it is multi-file by nature);
  no "single agent" option. If `Agent` is unavailable, run the degraded sequential-batch fallback and
  say so.
- **Input source:** the most recent `.coding-standards/reviews/<ts>.md` report, or an in-session
  review's findings. If neither exists, run a Review first to produce the ledger.

---

## Files touched

- `references/orchestrator-pipeline.md` — add the `MODE: fix` pipeline shape (the diagram above), the
  partition rule, the fan-out dispatch loop, the ledger, verify, and report steps. Add Fix to the
  pipeline invariants (orchestrator writes; per-file fan-out; ledger completeness; max 2 re-fix
  passes).
- `workers/fix-agent.md` — new brief for the per-file fix specialist.
- `SKILL.md` — add Fix to the mode routing (Step 0.5 outcomes + Step 1.5 note + the Mode section);
  add a Fix task-list shape to Step 1.6.
- `references/review-report.md` — note that a report is the input to Fix mode, and that finding IDs
  (stable per report) are what the ledger tracks.

## Out of scope

- Changing what Review mode reports (Fix consumes the existing report format; only a stable per-finding
  ID is added if not already present).
- The ST-008 rule / hook (separate, prior spec).
- Parallelizing Phase A structural fixes beyond the safe barrel-then-importer ordering.

## Acceptance

- `orchestrator-pipeline.md` documents a `MODE: fix` shape with: ledger, structural-vs-file-local
  partition, per-file parallel fan-out (one file's content + its findings per agent), verify pass,
  and a ledger-based report.
- `workers/fix-agent.md` exists with the input/output contract above and the "no silent skips /
  deferred-with-reason" rule.
- `SKILL.md` routes "fix the findings" to Fix mode, forces the orchestrator pipeline (with the
  Agent-unavailable fallback stated), and seeds a Fix task list.
- The documented flow never permits a silent partial: every finding ends `fixed` or
  `deferred(reason)`, and the final report enumerates deferrals.
- Dogfent: the new/edited markdown passes the skill's own hooks.
