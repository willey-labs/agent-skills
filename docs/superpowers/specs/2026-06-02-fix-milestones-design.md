# Design: Milestone-driven Fix mode — persisted plan, tracked to done

**Date:** 2026-06-02
**Skill:** `coding-standards`
**Status:** Approved design — pending implementation plan
**Builds on:** `2026-05-30-fix-mode-fanout-design.md` (shipped — this extends `MODE: fix`)

---

## Problem

Two failures observed on large reviews:

1. **Review chat output is a wall.** The full finding tables are printed to chat *on top of* the
   report file. On a big scope the user has to read all of it before anything can move.
2. **Fix runs lose track.** The completeness ledger from the fan-out spec lives **only in the
   conversation**. On a large fix the session balloons (and eventually compacts), and the ledger —
   the one thing recording what is fixed vs pending — is exactly what gets lost. The skill also
   asks "which findings should we fix first?" triage questions mid-session, adding to the sprawl.

Root cause: there is no **persisted, resumable progress state** and no **chunking**. The work is
one giant ledger held in fragile context, reported as one giant dump.

The fix: persist the ledger to disk as a **milestone plan**, work milestone-by-milestone to done
(Factory-Droid style), and report one compact status line per milestone instead of re-dumping
findings.

---

## Decisions (resolved with the user, 2026-06-02)

| Decision | Choice |
|---|---|
| Autonomy | Approve the milestone plan **once**, then run all milestones autonomously. Stop only on a real blocker. |
| Granularity | M1 = structural fixes (when any exist); then one milestone per module/folder (the nearest feature/module folder per the resolved structure; top-level directory as fallback), ordered by must-fix count descending. |
| "Done" means | One **git commit per milestone** (skipped with a note if the tree was dirty at run start). |
| State | On-disk plan file under `.coding-standards/fixes/`. The review report stays immutable input. |
| Resume | Any session (including a fresh one) continues from the first non-done milestone. No re-approval. |
| Harness mirroring | One harness task (TaskCreate) per milestone where the tool exists — display only, never source of truth. |
| Integration | Extend `MODE: fix` in place — no new mode, no new routing question. |

---

## Design

### 1. Trigger + threshold

`MODE: fix` becomes milestone-driven when the source report exceeds **20 findings or 10 files
with findings**, counted over **must-fix + should-fix** (the default scope — the count must be
decidable before the approval gate exists; a `consider` opt-in at approval can only add work to
an already-milestone-driven run). Below the threshold, the existing single-pass fix pipeline
runs unchanged.

Review mode uses the **same threshold**, counted over the whole report, for chat output: above
it, chat prints only the Summary
line, the must-fix table, the should-fix/consider **counts**, and the report path. The full
tables live in the report file only. Below the threshold, chat output is unchanged.

The threshold values are stated once in `orchestrator-pipeline.md` and referenced everywhere
else — one place to tune.

### 2. The plan file

Path: `<root>/.coding-standards/fixes/<review-ts>.md` — named after the report it consumes
(1:1 link), gitignored via the existing `.coding-standards/` ignore line. Created at fix start,
**before any write**.

Shape:

```markdown
# Fix plan — from reviews/2026-06-02-141503.md

- **Source report:** .coding-standards/reviews/2026-06-02-141503.md
- **Scope:** must-fix + should-fix (consider: excluded)
- **Commit policy:** commit per milestone (tree clean at start: yes)
- **Approved:** 2026-06-02-142010
- **Status:** in_progress (M3 of 7)

## M1 — structural — done — commit a1b2c3d
- [x] F004 — src/auth/index.ts — ST-002 — add barrel
- [x] F011 — src/billing/invoice.ts:3 — ST-003 — rewrite deep import

## M2 — src/auth (5 findings) — done-with-deferrals — commit d4e5f6a
- [x] F001 — src/auth/login.ts:42 — FN-005 — group args into options object
- [ ] F002 — src/auth/session.ts:18 — EH-002 — **deferred: re-fix failed after 2 passes**

## M3 — src/billing (8 findings) — in_progress
- [ ] F015 — src/billing/invoice.ts:77 — NM-003 — rename Hungarian prefix
...
```

Milestone statuses: `pending` → `in_progress` → `done` | `done-with-deferrals`. Findings keep
their report F-IDs; per-finding state is the checkbox plus a bold `deferred: <reason>` note when
applicable. The timestamp comes from the shell (`date +%Y-%m-%d-%H%M%S`), same as the report.

The file is rewritten **immediately after each milestone verifies**, before the chat status
line. Disk is the source of truth; chat is display.

### 3. Scope at approval

The single approval moment shows the milestone list with a severity breakdown per milestone and
asks scope **once**: default is **must-fix + should-fix**; `consider` findings are included only
if the user opts in here. The threshold in §1 is evaluated against the approved scope. After
approval, no further questions for the rest of the run.

### 4. Execution loop

Per milestone, in plan order:

1. **Fan out** per-file fix agents — the existing `workers/fix-agent.md` contract, unchanged
   (one file's content + its scoped findings per agent; orchestrator owns all writes).
2. **Verify** with `hooks/review-files.py` over **that milestone's files only**. Max 2 re-fix
   passes per file, then `deferred(reason)` — the existing rule, now recorded in the plan file.
3. **Update the plan file** (statuses, checkboxes, deferral notes).
4. **Commit**: `fix(standards): <milestone scope> — <n> findings [M<k>/<total>]`. Skipped with
   a note in the plan header if the working tree was dirty when the run started.
5. **Emit one chat line**: `M3/7 done — src/billing: 8 fixed, 0 deferred — abc1234`.

Findings are never re-dumped into chat during the run. A real blocker stops the run with the
milestone left `in_progress` and a note in the plan file saying what blocked it.

### 5. Resume

Trigger: "continue the fix" / "resume the fix" (and Fix-mode routing when a non-done plan file
exists and the user asks to fix the same report). Procedure:

1. Find the newest `.coding-standards/fixes/*.md` with non-done milestones.
2. Re-verify the files of any `in_progress` milestone (crash protection — a write may have
   landed without its ledger update), reconcile checkboxes against reality.
3. Continue the loop from §4. No re-approval — the plan header records the original approval.

### 6. Harness task mirroring

Where a harness task tool (TaskCreate / TaskUpdate) is available, create one task per milestone
at plan approval and update statuses as the loop runs. Display only — if the task tools are
absent (Cursor, Codex, OpenCode, …), skip silently. The plan file never depends on them.

---

## Files touched

- `references/orchestrator-pipeline.md` — milestone shape inside `MODE: fix`: threshold, plan
  build, approval gate, the per-milestone loop, resume, blocker handling. Threshold constants
  live here.
- `references/fix-plan.md` — **new**, sibling to `review-report.md`: plan-file format, statuses,
  update discipline (write-after-verify), resume procedure.
- `SKILL.md` — Fix mode section: threshold + milestone behavior + resume trigger phrases;
  Review mode step 5: trimmed chat output above threshold; Step 1.6: harness mirroring note.
- `references/review-report.md` — one note: above the threshold, chat prints summary + must-fix
  + counts + path; the file remains complete.
- `workers/fix-agent.md` — **unchanged** (contract already fits).

## Out of scope

- Changing the fix-agent contract or the per-file fan-out mechanics (prior spec, shipped).
- Changing the review report format — the plan keys on existing F-IDs.
- Merging plans across multiple reviews (one plan per report).
- Auto-push, PR creation, or any remote git action.
- Severity-gated checkpoints (explicitly rejected in favor of plan-once autonomy).

## Acceptance

- Above the threshold, Fix mode persists the plan file **before any write**; below it, behavior
  is byte-for-byte today's single-pass fix.
- The plan file is updated after every milestone verify, before the chat line; a kill -9 at any
  point loses at most one milestone's ledger update, which resume's re-verify reconciles.
- One chat line per completed milestone; finding tables are never re-printed during a fix run.
- One commit per milestone in the stated format; dirty-tree runs skip commits and say so in the
  plan header.
- "Continue the fix" in a fresh session resumes from the first non-done milestone with no
  re-approval and no repeated questions.
- Review mode above the threshold prints summary + must-fix + counts + path only.
- Harness tasks mirror milestones where the tools exist and are never read back as state.
- Dogfood: all new/edited markdown passes the skill's own hooks.
