# Orchestrator pipeline

The full protocol for the **orchestrator** execution shape. You arrive here from SKILL.md Step 5 — the task is a new feature, a 2+-file change, a diff/PR review, or the user picked "Multiple agents" / invoked `/coding-standards`. Read this file fully before dispatching Worker 1.

> **Paths in this file** (`workers/…`, `hooks/…`, `references/…`) are relative to the **skill root** — the directory that holds `SKILL.md`, one level up from this `references/` folder.

## Contents

- [The orchestrator's job](#the-orchestrators-job)
- [Worker roster](#worker-roster)
- [Pipeline shape](#pipeline-shape)
- [How to dispatch a worker](#how-to-dispatch-a-worker)
- [After all workers complete — Write mode](#after-all-workers-complete-write-mode)
- [After all workers complete — Review mode](#after-all-workers-complete-review-mode)
- [Fix mode (`MODE: fix`)](#fix-mode-mode-fix)
- [Tell the user what happened](#tell-the-user-what-happened)
- [Pipeline invariants](#pipeline-invariants)

## The orchestrator's job

You (the main agent) are now the **orchestrator**. You do not apply rules yourself; you coordinate three sequential workers. Workers never write to disk — you do the final Write at the end, so the hooks run on the final, complete code (not on Worker 1's placeholder bodies or Worker 2's error-handling-free draft). This is a **process invariant, not a platform guarantee**: a `general-purpose` subagent inherits the project's `Write|Edit` PreToolUse hooks and *could* write if it ignored its brief, so the briefs forbid it (`Output JSON only`). If a worker writes prematurely, the hook simply blocks the incomplete code and you re-dispatch. If your host lets you restrict a subagent's tools, dispatch the workers without `Write`/`Edit`/`MultiEdit` to enforce this structurally.

## Worker roster

| Worker | Owns | Brief file |
|---|---|---|
| **Worker 1 — Structure & Architecture** | ST-*, OD-001, OD-002, OD-004, OD-005, DP-001 to DP-005, DP-007, `<framework>/structure.md` | `workers/worker-1-structure.md` |
| **Worker 2 — Code Quality (line level)** | FN-001 to FN-009, NM-*, OD-003, OD-006, FMT-* | `workers/worker-2-quality.md` |
| **Worker 3 — Failure Handling** | EH-*, FN-010 | `workers/worker-3-failure.md` |

DP-006 (KISS) is a per-worker lens. **DP-007 (DRY) is owned by Worker 1 at module/cross-feature scale** (its function-level twin FN-011 stays Worker 2's). Worker 1 also owns ST-009. FN-012 ("rewrite the draft, don't ship it") stays a shared lens. (FN-010, the idiomatic-failure-mechanism rule, is Worker 3's, not cross-cutting.)

## Pipeline shape

**Write mode:**
```
User task
  → Worker 1 outputs file skeletons (paths, imports, signatures, placeholder bodies)
  → Worker 2 outputs files with function bodies, names, formatting, Demeter fixes
  → Worker 3 outputs final files with error boundaries, async safety, idiomatic failure
  → Orchestrator writes files (one Write call per file; hooks fire here on final code)
```

**Review mode:**
```
User task (diff/PR/file)
  → Phase 0 (Comprehend): orchestrator builds the structure map (references/structure-map.md) over the
    tree, confirms it with the user once (large reviews), persists it. Skipped below the scope threshold.
  → Worker 1 (Structure) — receives the MAP; reports structural findings as deltas against it + its rules
  → Worker 2 (Quality) → Worker 3 (Failure)
  → Orchestrator runs hooks/review-files.py --json over the file set (deterministic pass, runs LAST)
  → Orchestrator merges all worker findings + linter findings, orders by file then rule, presents unified report
```

## How to dispatch a worker

For each worker N in {1, 2, 3}:

1. **Read the brief**: `workers/worker-N-<name>.md`. The frontmatter tells you `owns_rules`, `applies_as_lens`, `must_not_touch`. The body is the prompt template.
2. **Construct the dispatch prompt** by combining:
   - The full body of the worker's brief file
   - A trailing block:
     ```
     === INPUT ===
     TASK: <user's original task verbatim>
     SKILL_DIR: <absolute path to the installed skill root — substitute the real path, e.g. /home/me/.claude/skills/coding-standards>
     FRAMEWORK: <detected framework key from SKILL.md Step 3>
     STRUCTURE: <resolved structure from SKILL.md Step 4 — the chosen structures/<name>.md, the project's .coding-standards-structure custom layout, or the framework default structure.md>
     STRUCTURE_MAP: <the comprehension map from Phase 0 — the confirmed B→F→SF→U model + relationship deltas; omitted below the scope threshold>
     MODE: write | review
     WORKER_<N-1>_OUTPUT: <previous worker's JSON, omit for Worker 1>
     ```
   - **`SKILL_DIR` is mandatory and load-bearing.** The worker is a fresh `general-purpose` subagent
     cwd'd in the *user's* project; on a global install the references live under
     `~/.claude/skills/coding-standards/`, not the project. Substitute the real absolute path you were
     invoked from (the directory containing this skill's `SKILL.md`). Every "References to load" path in a
     brief resolves against it: `<SKILL_DIR>/references/common/structure.md`. A `STRUCTURE` value naming
     `structures/<name>.md` likewise resolves to `<SKILL_DIR>/references/<framework>/structures/<name>.md`.
     Without it the worker cannot load the worked examples the review depends on and silently reviews from
     memory — the exact thin-review failure step 5 rejects.
   - When Phase 0 produced a map, include `STRUCTURE_MAP`. Workers treat it as the intended shape: a
     file's placement, a folder's promotion, a feature's duplication are judged against the map, not
     re-derived per file.
3. **Call the `Agent` tool** with:
   - `subagent_type: "general-purpose"`
   - `description: "coding-standards worker <N>"`
   - `prompt`: the constructed prompt
4. **Parse the worker's JSON output.** If parsing fails:
   - Retry once with a clarifying message: "Your previous response was not valid JSON. Return ONLY the JSON object specified in the brief."
   - If still failing, fall back to inline (load all references yourself, do the work, write files).
5. **Validate the output**:
   - **Write mode:** worker only modified files it had authority over (check `must_not_touch`); its `changes_made` / `decisions` / `error_handling_added` cite a rule code it owns; it introduced no abstractions outside its rule list (no new Strategy patterns from Worker 2; no new layers from Worker 3).
   - **Review mode:** every owned **enumerable `common/` rule** (each `ST-*`, `OD-*`, etc. the worker owns) appears in exactly one of `findings` / `passed` / `skipped` — **reject (and re-dispatch) a review that silently drops one**, since that is the thin-review failure mode. Worker 1 additionally owns the framework structure rules (`<framework>/*`), which aren't a fixed enumerable list — so for those require a single **framework-coverage line** in `passed`/`skipped` stating the structure file was checked against the resolved layout (e.g. `"nextjs/structure: checked against feature-first — placement conforms"`), not a per-rule enumeration. Each `findings` entry cites a rule and carries `file`, `line`, and a concrete `fix` (no severity — every finding is a violation to fix).
6. **If validation fails**, redispatch the worker with the specific violation noted. After one retry, fall back to inline.

> **TodoWrite (only if you seeded a list in SKILL.md Step 6):** mark worker N `in_progress` as you dispatch it and `completed` once its output validates (step 5 above). Tick the bracketing items the same way — the final write-and-hooks (Write mode), or the linter pass and merge-and-present (Review mode, where the linter runs *after* the three workers) — as you reach each. If you didn't seed a list (TodoWrite unavailable, or inline single-file work), ignore this.

## After all workers complete (Write mode)

7. **Take Worker 3's `files` object.** For each `path → content`:
   - If file does not exist: call `Write` with the content.
   - If file exists: read it, compute the minimal edit, call `Edit`. (For new code, Write is almost always the right call.)
8. **The hooks fire here**, on the final content, exactly once per file. If a hook blocks, the orchestrator must:
   - Read the hook's stderr message.
   - Identify which worker should have caught the violation.
   - Redispatch that worker with the hook's feedback included.
   - Retry the Write.
   - If retry fails twice, surface the error to the user with the hook's diagnostic.
9. **Migration offer (messy/custom project).** If Worker 1 returned a non-empty `existing_mismatches` array, do **not** reorganize those files — that's out of scope for the task. After writing the new files, surface a single line: `N existing files don't match {structure} — want a separate migration pass?` and let the user opt in.

## After all workers complete (Review mode)

7. **Run `hooks/review-files.py --json`** over the file set now — *after* the three workers, as the final deterministic pass. Every finding it returns is a violation to fix: the *existence* of the finding is deterministic and never re-litigated (an `any` is an `any`). For the ST-008 decl-count block, the *remedy* is the reviewer's judgement — a cohesive split, OR a recorded exemption (`.coding-standards-ignore` + reason, logged `accepted`) when the file is one cohesive job the proxy miscounts. A split that creates scatter or copies a sibling's machinery is itself an ST-008 + DP-007 violation, not a fix.
8. **Merge** every worker's `findings` array + the linter findings. **Dedupe** by `(file, line, rule)` — when a worker finding and a linter finding collide, keep one. Then **order by file, then rule code** — there are no severity tiers; every finding is a violation to fix. The workers' `passed` / `skipped` arrays are the **coverage proof** — use them to state which rules were checked and clean, so the report is visibly comprehensive rather than a short list of hits.
9. **Write the report file**, then **present** it to the user as a structured PASS/FAIL table — in full at or below the scope threshold; above it, trim chat to the shape defined in `references/review-report.md` (the file keeps everything). Cite rule codes. Do not editorialize. The report file — path, timestamped name, gitignore handling, the mandatory self-describing `Structure baseline` field, and the Markdown shape — is specified in `references/review-report.md`. End by telling the user the report path.
10. **Verify the structure baseline.** Run `python3 <skill-dir>/hooks/check-review-report.py <report.md>` (pass `--root <sub-project>` in a monorepo). Exit `2` means the report asserts a structure with no `.coding-standards-structure` on disk — `STRUCTURE_MAP` was supposed to be built and recorded before Worker 1 (see the Step 7a invariant); resolve + record it and rewrite the report before reporting done. Exit `1` is a declared skip — surface the reason. This is the deterministic back-stop: the pipeline cannot report a grounded structural review while the baseline it names doesn't exist.

## Fix mode (`MODE: fix`) — apply review findings at scale

Fix mode applies an existing review's findings across many files. It does **not**
run the Worker 1→2→3 sequence — the unit of independent work is a *file*, not a rule
domain — so it **fans out one fix-agent per file**. This is the path that scales: a
large finding set *triggers* fan-out instead of overflowing one context.

**Input:** the most recent `.coding-standards/reviews/<ts>.md` report (or an
in-session review's findings). If none exists, run Review first to produce one. If a
non-done fix plan (`.coding-standards/fixes/<ts>.md`) already exists for that report,
resume it instead of starting over — see "Resume" below.

**Gate the input on a grounded structure baseline.** Before fanning out, run
`python3 <skill-dir>/hooks/check-review-report.py <input-report.md>`. Exit `2` means
the report's structural findings have no recorded baseline behind them — fixing them
(reorganizing files against a structure that was never resolved) is unsound. Stop:
resolve + record the structure and re-run Review to produce a grounded report, then
fix. Exit `1` (declared skip) proceeds, but tell the user the fix carries no structural
baseline.

**Scope threshold — the one place these numbers live:** a fix is **milestone-driven**
when the report holds **more than 20 findings or more than 10 files with findings**,
counted over **all** findings (there are no severity tiers — every finding is in
scope). At or below that, run the single-pass fix. Review mode reuses the same
numbers — counted over the whole report — to trim its chat output (see
`references/review-report.md`).

### Single-pass fix (at or below the threshold)

1. **Build the completeness ledger.** One row per finding:
   `{ id, file, line, rule, status }`, `status = pending`. The id is the
   per-finding id from the review report (see `references/review-report.md`).

2. **Partition findings:**
   - **STRUCTURAL / cross-file** — ST-002 (barrels/`index`), ST-003 (deep imports),
     ST-008 (file splits), moves/renames. These have ordering dependencies.
   - **FILE-LOCAL** — FN-*, NM-*, EH-*, FMT-*, OD-003. Independent per file.

3. **Phase A — structural, coordinated.** Do these yourself (orchestrator), in order,
   because later steps depend on earlier ones:
   a. create/extend barrel `index` files (ST-002);
   b. rewrite deep imports to the new public entries (ST-003);
   c. apply ST-008 splits (create named sibling files, move declarations);
   d. **re-check each folder the splits added files to:** if 3+ flat siblings now
      share a theme, the folder has earned a sub-feature promotion (ST-008's Rule
      of Three) that is **not** in the ledger — record it as a *promotion
      candidate* (folder + themed cluster). Don't perform it: fix mode never
      expands its own ledger mid-run. Candidates surface as offers in the final
      report.
   e. **rewrite the structure record:** once the moves / splits / renames are
      applied, rewrite `.coding-standards-structure`'s `layout:` to the **achieved**
      tree, so the committed record matches what's now on disk (SKILL.md Step 4). If a
      move was deferred, mirror what's actually there — the ledger/report carries the
      open breach; the record never claims a structure that isn't on disk.
   Each write goes through the orchestrator, so the hooks fire. Update the ledger.
   Independent barrels may fan out, but an import rewrite runs only after the barrel
   it targets exists.

4. **Phase B — file-local, fan-out (parallel, one agent per file).** For each file
   that still has file-local findings, dispatch `workers/fix-agent.md` via the
   `Agent` tool (`subagent_type: "general-purpose"`), batched to the host's
   concurrency cap. The agent's INPUT carries **only that file's current content and
   its own findings** — never the whole set — with these fields:
   - `FILE_PATH` — absolute path of the one file being fixed
   - `CURRENT_CONTENT` — the file's current full content
   - `FINDINGS` — this file's subset only (JSON array of `{ id, rule, line, fix }`)
   - `FRAMEWORK` — detected framework key
   - `STRUCTURE` — resolved project structure
   Parse the returned JSON
   (`{ path, fixed_content, fixed[], deferred[] }`), then **you** write the file
   (hooks fire per file). Update the ledger: each finding → `fixed` or
   `deferred(reason)`.

5. **Verify.** Run `hooks/review-files.py --json` over every changed file. If a
   finding that was marked `fixed` still trips the linter, flip it to `pending` and
   re-dispatch that one file (max **2** re-fix passes per file; then
   `deferred(reason="re-fix failed")`).

6. **Report against the ledger.** State `N fixed · A accepted (not violations — each
   with reason) · D deferred (OPEN BREACHES — each with reason)`, across K files. If
   D > 0 the run reports `done-with-open-breaches (D unresolved)`, lists every open
   breach, asks the user to resolve each, and never prints `done` until they are. An
   `accepted` finding's reason must say why it is not a violation. An incomplete run
   says exactly what remains and why — it never stops silently. If Phase A recorded
   promotion candidates, add one line per folder — `<folder> now holds <n> flat
   files; <x, y, z> share a theme and have earned a sub-feature folder — want a
   promotion pass?` — the same opt-in shape as the Write-mode migration offer.

### Milestone-driven fix (above the threshold)

A big fix is chunked into **milestones**, persisted to a plan file, and worked to done
autonomously — approve once, then no more questions. The plan-file format, statuses,
and resume mechanics live in `references/fix-plan.md`; this is the orchestration:

1. **Build the plan.** Build the ledger and partition exactly as in Single-pass fix steps
   1–2, then group into milestones:
   - **M1 — structural** (only when structural findings exist): every ST-002 /
     ST-003 / ST-008 / move-rename finding, in the Phase-A order (barrels →
     deep-import rewrites → ST-008 splits). M1 is derived from the structure map's
     relationship deltas as well as the report's ST-* findings — de-nest a misfiled
     peer (ST-009), consolidate a split feature (ST-001), route duplicate machinery to
     its shared home (DP-007), promote a themed cluster (ST-008). The map is read from
     `.coding-standards/structure-map.md`; if absent (review predated this), build it
     first. When M1's moves are applied, rewrite `.coding-standards-structure`'s
     `layout:` to the achieved tree (as in Single-pass step 3e).
   - **M2…Mn — one per module:** group the file-local findings by the nearest
     feature/module folder per the resolved STRUCTURE (top-level directory as
     fallback). Order milestones by total finding count descending, then path.
   Record the commit policy: commits happen only if the root is a git repo **and**
   the working tree was clean (`git status --porcelain` empty) at run start;
   otherwise the plan header notes why commits are skipped.

2. **One approval, then autonomy.** Present the milestone list compactly — one line
   per milestone: scope (the module) and finding count — and ask **one** question: go
   ahead? Every finding is in scope; there is no severity sub-choice to make. Write the
   plan file **before any write to user code**. If the host has a task-list tool, create
   one task per milestone now (display mirror only — the plan file is the source of
   truth). After this point, ask nothing until the run ends or blocks.

3. **The milestone loop.** For each milestone in plan order:
   a. Execute it — M1 via the Phase-A coordination, module milestones via the
      Phase-B per-file fan-out (same mechanics, scoped to this milestone's files).
   b. Verify with `hooks/review-files.py --json` over **this milestone's files
      only**; max 2 re-fix passes per file, then `deferred(reason)`.
   c. **Update the plan file first** — statuses, checkboxes, deferral notes, and any
      promotion candidates from Phase-A step d (recorded under the plan's
      `## Follow-ups` section, see `references/fix-plan.md`) — before the commit and
      the chat line.
   d. Commit (when the policy allows):
      `fix(standards): <milestone scope> — <n> findings [M<k>/<total>]`.
   e. Emit **one chat line**:
      `M<k>/<total> done — <scope>: <n> fixed, <d> deferred — <short-hash>`
      (`no commit` in place of the hash when the policy skips commits).
      Never re-print finding tables during the run.

4. **Blockers.** A real blocker (a hook keeps rejecting past the re-fix budget, a fix
   needs a user decision, the host dies mid-run) stops the run: leave the milestone
   `in_progress`, write what blocked it into the plan header (`Status: blocked
   (M<k>: <reason>)`), tell the user in one line. "Continue the fix" resumes from
   there — per the blocked-plan rule in `references/fix-plan.md`: surface the
   recorded reason first; a needed user decision is the sole exception to
   no-repeated-questions.

5. **Final report.** When every milestone is terminal, report against the plan file:
   `N fixed · A accepted (not violations — each with reason) · D deferred (OPEN
   BREACHES — each with reason)`, across K files in T milestones. If D > 0 the run
   reports `done-with-open-breaches (D unresolved)`, lists every open breach, asks
   the user to resolve each, and never prints `done` until they are — plus every
   `## Follow-ups` entry as a one-line offer (promotion candidates from Phase-A step
   d). Same ledger-completeness rule as single-pass: an incomplete run says exactly
   what remains and why; it never stops silently.

### Resume

"continue the fix" / "resume the fix" — from any session, including a fresh one:
follow the resume procedure in `references/fix-plan.md` (newest non-done plan,
re-verify any `in_progress` milestone's files, reconcile checkboxes against reality),
then continue at step 3 of "Milestone-driven fix" above. **No re-approval** — the
plan header records the original approval and scope.

**Fallback when `Agent` is unavailable** (Cursor/Codex/OpenCode): run the phases
yourself in batches, one file at a time, still driven by the ledger — and by the plan
file when milestone-driven — and report the same way. Announce that fan-out is
unavailable in this host.

## Tell the user what happened

After the pipeline completes, summarize:

```
Worker 1 (Structure):
  - Placed 2 files per ST-001 capability layout
  - Designed <entity> as a data structure (OD-002)
  - Wired DI per DP-005 — <service> depends on a <gateway> interface

Worker 2 (Quality):
  - Renamed 4 placeholders to intent-revealing names (NM-001)
  - Extracted 30-line function into 3 helpers (FN-001)
  - Fixed 1 Demeter chain (OD-003)

Worker 3 (Failure):
  - Added EH-002 boundary translation around the external SDK call
  - Awaited 1 floating Promise (EH-004)

Files written: <list>. Hooks passed.
```

## Pipeline invariants

- **Workers never call `Write`/`Edit`.** They emit code as JSON values. Only you (the orchestrator) write to disk.
- **Hooks fire on the orchestrator's final Write** per file, after Worker 3 — because workers emit JSON, not disk writes (a process invariant; see "The orchestrator's job" above). If a worker writes prematurely, the hook blocks the incomplete code and you re-dispatch.
- **No worker can modify rules outside its `owns_rules` list.** Validate before accepting output.
- **No retries past 2.** If a worker fails twice, fall back to inline.
- **Sequential, not parallel.** Worker N's output is Worker N+1's input. Do not dispatch Worker 2 before Worker 1 completes.
- **Fix mode fans out by file, not by rule domain.** One fix-agent per file, each
  given only that file's content + its findings. Structural (cross-file) fixes run
  first, coordinated by the orchestrator; file-local fixes fan out in parallel.
- **Fix mode is ledger-complete.** Every finding ends `fixed`, `accepted`, or
  `deferred` (with reason); a silent partial result is a failure. A run with any
  `deferred` (open-breach) finding reports `done-with-open-breaches`, never `done`,
  until the user resolves them. Max 2 re-fix passes per file.
- **Fix mode never expands its own ledger.** A folder promotion earned by its own
  ST-008 splits (Phase-A step d) is recorded and offered after the run — never
  performed mid-run.
- **Milestone fixes are disk-anchored.** Above the scope threshold the plan file
  (`references/fix-plan.md`) is the source of truth: written before any code write,
  updated after every milestone verify, one commit and one chat line per milestone,
  finding tables never re-dumped to chat. Approval happens exactly once, at plan
  time; resume never re-asks.
