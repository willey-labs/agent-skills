# Milestone-Driven Fix Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Above a scope threshold, Fix mode persists a milestone plan to disk, gets one approval, then runs every milestone to done autonomously — resumable from any session; Review mode trims its chat output at the same threshold.

**Architecture:** Pure instruction-file change to the `coding-standards` skill — no hooks or Python touched. The threshold numbers live in exactly one place (`orchestrator-pipeline.md`); `SKILL.md` and `review-report.md` reference them without restating. A new `references/fix-plan.md` specifies the plan-file artifact, sibling to `review-report.md`. `workers/fix-agent.md` is unchanged.

**Tech Stack:** Markdown instruction files; verification via `grep` consistency checks and the repo's own write-time hooks (dogfood).

**Spec:** `docs/superpowers/specs/2026-06-02-fix-milestones-design.md`
**Branch:** `feat/fix-milestones` (already created; spec committed)

---

### Task 1: Create `references/fix-plan.md` (the plan-file artifact spec)

**Files:**
- Create: `skills/coding-standards/references/fix-plan.md`

- [ ] **Step 1: Write the file with exactly this content**

````markdown
# Fix plan file (milestone ledger)

A milestone-driven fix run (`orchestrator-pipeline.md` → Fix mode) persists its plan and progress to a Markdown file so the run survives session bloat, compaction, and restarts. The file — not the conversation — is the source of truth for what is fixed, pending, or deferred. Chat shows one status line per milestone; this file holds everything else.

## Path + lifecycle

1. Path: `<root>/.coding-standards/fixes/<review-ts>.md`, where `<review-ts>` is the timestamp of the source review report (`.coding-standards/reviews/<review-ts>.md`) — a 1:1 link, **not** a new timestamp. Create `.coding-standards/fixes/` if absent.
2. Created at fix start, with the approved scope, **before any write to user code**.
3. Gitignored via the existing `.coding-standards/` line and excluded from future reviews the same way as reports (`hooks/_exclusions.py`).
4. Rewritten in full **immediately after each milestone verifies**, before the chat status line. A crash therefore loses at most one milestone's ledger update — resume's re-verify reconciles it.
5. Timestamps come from the shell (`date +%Y-%m-%d-%H%M%S`), never from the agent.

## File shape

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
```

## Statuses

- **Milestone:** `pending` → `in_progress` → `done` | `done-with-deferrals`.
- **Finding:** checked = fixed; unchecked with a bold `**deferred: <reason>**` suffix = deferred; unchecked plain = pending. Finding IDs are the report's `F<NNN>` ids — never renumber or drop them.
- **Header `Status:`** mirrors the run: `in_progress (M<k> of <total>)` while looping; `done` / `done-with-deferrals` when every milestone is terminal; `blocked (M<k>: <one-line reason>)` when a blocker stopped the run.

## Resume procedure

Triggered by "continue the fix" / "resume the fix", or by Fix mode finding a non-done plan for the requested report.

1. Find the newest `.coding-standards/fixes/*.md` whose header `Status:` is not terminal (`done` / `done-with-deferrals`).
2. For any milestone marked `in_progress`, re-run `hooks/review-files.py --json` over that milestone's files and reconcile: a finding that no longer trips and whose fix is visibly applied → check it; a finding still tripping → leave pending. (Crash protection — a write may have landed without its ledger update.)
3. Continue the milestone loop from the first non-done milestone. **No re-approval, no repeated questions** — the header records the original approval and scope.

## Invariants

- Disk is the source of truth; harness task lists (`TaskCreate`/`TodoWrite`) only mirror it and are never read back as state.
- Every finding in approved scope ends checked or deferred-with-reason — the same ledger-completeness rule as the single-pass fix. Silence is failure.
````

- [ ] **Step 2: Verify the file landed and the hooks didn't block**

Run: `ls -la skills/coding-standards/references/fix-plan.md`
Expected: file exists (the Write succeeding already proves `block-junk-paths.py` accepted the name).

- [ ] **Step 3: Commit**

```bash
git add skills/coding-standards/references/fix-plan.md
git commit -m "add references/fix-plan.md — persisted milestone ledger format

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Milestone path + resume in `orchestrator-pipeline.md`

**Files:**
- Modify: `skills/coding-standards/references/orchestrator-pipeline.md` (Fix mode section, lines ~103–157; Pipeline invariants, lines ~188–192)

Three exact-string edits. The existing single-pass steps 1–6 are kept verbatim under a new h3.

- [ ] **Step 1: Edit — input paragraph → input + threshold + single-pass heading**

Replace this exact text:

```markdown
**Input:** the most recent `.coding-standards/reviews/<ts>.md` report (or an
in-session review's findings). If none exists, run Review first to produce one.
```

with:

```markdown
**Input:** the most recent `.coding-standards/reviews/<ts>.md` report (or an
in-session review's findings). If none exists, run Review first to produce one. If a
non-done fix plan (`.coding-standards/fixes/<ts>.md`) already exists for that report,
resume it instead of starting over — see "Resume" below.

**Scope threshold — the one place these numbers live:** a fix is **milestone-driven**
when the report holds **more than 20 findings or more than 10 files with findings**,
counted over must-fix + should-fix (the default scope — decidable before the approval
gate exists; a `consider` opt-in at approval only adds work to an already-milestone-
driven run). At or below that, run the single-pass fix. Review mode reuses the same
numbers — counted over the whole report — to trim its chat output (see
`references/review-report.md`).

### Single-pass fix (at or below the threshold)
```

- [ ] **Step 2: Edit — replace the fallback paragraph with milestone loop + resume + generalized fallback**

Replace this exact text:

```markdown
**Fallback when `Agent` is unavailable** (Cursor/Codex/OpenCode): run Phases A and B
yourself in batches, one file at a time, still driven by the ledger, and report the
same way. Announce that fan-out is unavailable in this host.
```

with:

```markdown
### Milestone-driven fix (above the threshold)

A big fix is chunked into **milestones**, persisted to a plan file, and worked to done
autonomously — approve once, then no more questions. The plan-file format, statuses,
and resume mechanics live in `references/fix-plan.md`; this is the orchestration:

1. **Build the plan.** Build the ledger and partition exactly as in single-pass steps
   1–2, then group into milestones:
   - **M1 — structural** (only when structural findings exist): every ST-002 /
     ST-003 / ST-008 / move-rename finding, in the Phase-A order.
   - **M2…Mn — one per module:** group the file-local findings by the nearest
     feature/module folder per the resolved STRUCTURE (top-level directory as
     fallback). Order milestones by must-fix count descending, then total findings
     descending, then path.
   Record the commit policy: commits happen only if the root is a git repo **and**
   the working tree was clean (`git status --porcelain` empty) at run start;
   otherwise the plan header notes why commits are skipped.

2. **One approval, then autonomy.** Present the milestone list compactly — one line
   per milestone: scope, finding count, severity breakdown — and ask **one** question:
   scope. Default **must-fix + should-fix**; `consider` findings join only if the user
   opts in here. Write the plan file with the approved scope **before any write to
   user code**. If the host has a task-list tool, create one task per milestone now
   (display mirror only — the plan file is the source of truth). After this point,
   ask nothing until the run ends or blocks.

3. **The milestone loop.** For each milestone in plan order:
   a. Execute it — M1 via the Phase-A coordination, module milestones via the
      Phase-B per-file fan-out (same mechanics, scoped to this milestone's files).
   b. Verify with `hooks/review-files.py --json` over **this milestone's files
      only**; max 2 re-fix passes per file, then `deferred(reason)`.
   c. **Update the plan file first** — statuses, checkboxes, deferral notes — before
      the commit and the chat line.
   d. Commit (when the policy allows):
      `fix(standards): <milestone scope> — <n> findings [M<k>/<total>]`.
   e. Emit **one chat line**:
      `M<k>/<total> done — <scope>: <n> fixed, <d> deferred — <short-hash>`.
      Never re-print finding tables during the run.

4. **Blockers.** A real blocker (a hook keeps rejecting past the re-fix budget, a fix
   needs a user decision, the host dies mid-run) stops the run: leave the milestone
   `in_progress`, write what blocked it into the plan header (`Status: blocked
   (M<k>: <reason>)`), tell the user in one line. "Continue the fix" resumes from
   there.

5. **Final report.** When every milestone is terminal, report against the plan file:
   `N of M findings fixed across K files in T milestones; D deferred` — plus every
   deferral with its reason. Same ledger-completeness rule as single-pass: an
   incomplete run says exactly what remains and why; it never stops silently.

### Resume

"continue the fix" / "resume the fix" — from any session, including a fresh one:
follow the resume procedure in `references/fix-plan.md` (newest non-done plan,
re-verify any `in_progress` milestone's files, reconcile checkboxes against reality),
then continue the milestone loop at step 3. **No re-approval** — the plan header
records the original approval and scope.

**Fallback when `Agent` is unavailable** (Cursor/Codex/OpenCode): run the phases
yourself in batches, one file at a time, still driven by the ledger — and by the plan
file when milestone-driven — and report the same way. Announce that fan-out is
unavailable in this host.
```

- [ ] **Step 3: Edit — add the milestone invariant**

Replace this exact text (the last invariant bullet):

```markdown
- **Fix mode is ledger-complete.** Every finding ends `fixed` or `deferred(reason)`;
  a silent partial result is a failure. Max 2 re-fix passes per file.
```

with:

```markdown
- **Fix mode is ledger-complete.** Every finding ends `fixed` or `deferred(reason)`;
  a silent partial result is a failure. Max 2 re-fix passes per file.
- **Milestone fixes are disk-anchored.** Above the scope threshold the plan file
  (`references/fix-plan.md`) is the source of truth: written before any code write,
  updated after every milestone verify, one commit and one chat line per milestone,
  finding tables never re-dumped to chat. Approval happens exactly once, at plan
  time; resume never re-asks.
```

- [ ] **Step 4: Verify the section structure**

Run: `grep -n "^### \|^## " skills/coding-standards/references/orchestrator-pipeline.md`
Expected: `## Fix mode (\`MODE: fix\`) — apply review findings at scale` followed by `### Single-pass fix (at or below the threshold)`, `### Milestone-driven fix (above the threshold)`, `### Resume`, then `## Tell the user what happened`.

Run: `grep -c "20 findings" skills/coding-standards/references/orchestrator-pipeline.md`
Expected: `1` (the numbers live here exactly once).

- [ ] **Step 5: Commit**

```bash
git add skills/coding-standards/references/orchestrator-pipeline.md
git commit -m "add milestone-driven path + resume to fix mode pipeline

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Route milestones in `SKILL.md` + trim big-review chat output + version bump

**Files:**
- Modify: `skills/coding-standards/SKILL.md` (frontmatter ~line 16; Step 0.5 ~line 121; Step 1.5 table ~line 204; Step 1.6 ~line 242; Review step 5 ~line 323; Fix section ~line 331)

Six exact-string edits. Note: SKILL.md references the threshold but never restates the numbers — they live only in `orchestrator-pipeline.md`.

- [ ] **Step 1: Edit — version bump**

Replace `  version: "4.4.0"` with `  version: "4.5.0"`.

- [ ] **Step 2: Edit — Step 0.5 Fix trigger phrases**

Replace this exact text:

```markdown
There is no picker entry for **Fix** — it's triggered by phrasing ("fix the findings" / "apply the
review"), which routes straight to Fix mode (the `MODE: fix` orchestrator pipeline, no run-mode question).
```

with:

```markdown
There is no picker entry for **Fix** — it's triggered by phrasing ("fix the findings" / "apply the
review", or "continue the fix" / "resume the fix" to pick up a non-done milestone plan), which routes
straight to Fix mode (the `MODE: fix` orchestrator pipeline, no run-mode question).
```

- [ ] **Step 3: Edit — Step 1.5 table row**

Replace this exact text:

```markdown
| Apply review findings ("fix the findings") | **Orchestrator pipeline, `MODE: fix`, always.** Per-file fan-out; no run-mode question. |
```

with:

```markdown
| Apply review findings ("fix the findings", "continue the fix") | **Orchestrator pipeline, `MODE: fix`, always.** Per-file fan-out; milestone-driven above the scope threshold; no run-mode question. |
```

- [ ] **Step 4: Edit — Step 1.6 milestone mirroring**

Replace this exact text:

```markdown
orchestrator-pipeline and Fix shapes add their worker/ledger stages — see `orchestrator-pipeline.md`.
```

with:

```markdown
orchestrator-pipeline and Fix shapes add their worker/ledger stages — see `orchestrator-pipeline.md`.
A milestone-driven fix adds one item per milestone at plan approval — a display mirror only; the plan
file on disk stays the source of truth.
```

- [ ] **Step 5: Edit — Review step 5 trimmed chat output**

Replace this exact text:

```markdown
   (`.coding-standards/reviews/<timestamp>.md`, gitignored) and tell the user the path — every review writes
   one, inline included.
```

with:

```markdown
   (`.coding-standards/reviews/<timestamp>.md`, gitignored) and tell the user the path — every review writes
   one, inline included. **Above the scope threshold** (defined once in `orchestrator-pipeline.md` → Fix
   mode), chat gets the Summary line, the must-fix table, the should-fix/consider counts, and the report
   path; the full tables live in the file only. At or below it, print everything as before.
```

- [ ] **Step 6: Edit — Fix mode section**

Replace this exact text:

```markdown
Triggered by "fix the findings" / "apply the review" / fixes requested right after a Review. Fix mode
**always runs as the orchestrator pipeline** (`MODE: fix`) — it's inherently multi-file: it fans out one
fix-agent per file, tracked by a completeness ledger so nothing is silently half-fixed. Don't offer a
"single agent" option. If `Agent` is unavailable, run the documented sequential-batch fallback and say so.

The full pipeline (ledger, structural-vs-file-local partition, per-file fan-out, verify, ledger report) is
in `references/orchestrator-pipeline.md` under "Fix mode". The input is the most recent
`.coding-standards/reviews/<ts>.md`; if none exists, run Review first.
```

with:

```markdown
Triggered by "fix the findings" / "apply the review" / fixes requested right after a Review — or by
"continue the fix" / "resume the fix" to pick up a non-done milestone plan. Fix mode **always runs as
the orchestrator pipeline** (`MODE: fix`) — it's inherently multi-file: it fans out one fix-agent per
file, tracked by a completeness ledger so nothing is silently half-fixed. Don't offer a "single agent"
option. If `Agent` is unavailable, run the documented sequential-batch fallback and say so.

**Above the scope threshold** (defined once in `orchestrator-pipeline.md` → Fix mode), the fix is
**milestone-driven**: build a persisted plan (`.coding-standards/fixes/<review-ts>.md`, format in
`references/fix-plan.md`), get **one** approval (scope: must-fix + should-fix by default, `consider`
only on opt-in), then run every milestone to done autonomously — fix, verify, update the plan file,
commit per milestone, one chat status line each. The plan file survives session loss; any session
resumes it without re-approval.

The full pipeline (ledger, partition, per-file fan-out, milestone loop, verify, report) is in
`references/orchestrator-pipeline.md` under "Fix mode". The input is the most recent
`.coding-standards/reviews/<ts>.md`; if none exists, run Review first.
```

- [ ] **Step 7: Verify no numbers leaked into SKILL.md**

Run: `grep -n "20 findings\|10 files" skills/coding-standards/SKILL.md`
Expected: no output (SKILL.md references the threshold by name only).

Run: `grep -c "fix-plan.md" skills/coding-standards/SKILL.md`
Expected: `1`.

- [ ] **Step 8: Commit**

```bash
git add skills/coding-standards/SKILL.md
git commit -m "route milestone-driven fix in SKILL.md, trim big-review chat output, bump 4.5.0

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Note trimmed chat output + plan-file link in `review-report.md`

**Files:**
- Modify: `skills/coding-standards/references/review-report.md` (intro, line 3; Finding IDs section, lines ~47–54)

- [ ] **Step 1: Edit — intro chat-print sentence**

Replace this exact text:

```markdown
Every review — orchestrator pipeline *and* inline single-agent — persists its merged result to a Markdown file so it's durable, diffable, and feedable to a later fix pass. The same content is also printed to the user; the file is an additional artifact, not a replacement for the chat summary.
```

with:

```markdown
Every review — orchestrator pipeline *and* inline single-agent — persists its merged result to a Markdown file so it's durable, diffable, and feedable to a later fix pass. The same content is also printed to the user — except above the scope threshold (defined once in `orchestrator-pipeline.md` → Fix mode), where chat gets the Summary line, the must-fix table, the should-fix/consider counts, and the report path, and the full tables live here only. The file is always complete either way.
```

- [ ] **Step 2: Edit — Finding IDs section, link to the plan file**

Replace this exact text:

```markdown
Keep ids stable for the life of the report file — never renumber after the report is
written.
```

with:

```markdown
Keep ids stable for the life of the report file — never renumber after the report is
written. A milestone-driven fix persists that ledger as a plan file —
`.coding-standards/fixes/<review-ts>.md`, same timestamp as this report — see
`references/fix-plan.md`.
```

- [ ] **Step 3: Commit**

```bash
git add skills/coding-standards/references/review-report.md
git commit -m "note trimmed big-review chat output + fix-plan link in review-report.md

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Cross-file consistency check (no commit unless fixes needed)

**Files:**
- Read-only verification across `skills/coding-standards/`

- [ ] **Step 1: Threshold numbers live in exactly one file**

Run: `grep -rln "20 findings" skills/coding-standards/`
Expected: only `skills/coding-standards/references/orchestrator-pipeline.md`.

- [ ] **Step 2: Every fix-plan reference resolves**

Run: `grep -rn "fix-plan.md" skills/coding-standards/ | grep -v "references/fix-plan.md:"`
Expected: hits in `orchestrator-pipeline.md` (3: milestone intro + resume + invariant), `SKILL.md` (1), `review-report.md` (1) — and the file itself exists at `skills/coding-standards/references/fix-plan.md`.

- [ ] **Step 3: Plan-file path is spelled consistently**

Run: `grep -rn "coding-standards/fixes/" skills/coding-standards/`
Expected: every hit uses `.coding-standards/fixes/<review-ts>.md` or `.coding-standards/fixes/<ts>.md` — no variant spellings (`fix/`, `fixplans/`).

- [ ] **Step 4: Resume phrases appear in both routing docs**

Run: `grep -rln "continue the fix" skills/coding-standards/`
Expected: `SKILL.md`, `references/orchestrator-pipeline.md`, `references/fix-plan.md`.

- [ ] **Step 5: Only if any check failed — fix the offending file and commit the correction**

```bash
git add -u skills/coding-standards/
git commit -m "fix cross-file consistency for milestone fix docs

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

(Skip this step entirely when steps 1–4 all pass.)
