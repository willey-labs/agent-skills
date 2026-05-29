# Orchestrator pipeline

The full protocol for the **orchestrator** execution shape. You arrive here from SKILL.md Step 1.5 — the task is a new feature, a 2+-file change, a diff/PR review, or the user picked "Multiple agents" / invoked `/coding-standards`. Read this file fully before dispatching Worker 1.

> **Paths in this file** (`workers/…`, `hooks/…`, `references/…`) are relative to the **skill root** — the directory that holds `SKILL.md`, one level up from this `references/` folder.

## Contents

- [The orchestrator's job](#the-orchestrators-job)
- [Worker roster](#worker-roster)
- [Pipeline shape](#pipeline-shape)
- [How to dispatch a worker](#how-to-dispatch-a-worker)
- [After all workers complete — Write mode](#after-all-workers-complete-write-mode)
- [After all workers complete — Review mode](#after-all-workers-complete-review-mode)
- [Tell the user what happened](#tell-the-user-what-happened)
- [Pipeline invariants](#pipeline-invariants)

## The orchestrator's job

You (the main agent) are now the **orchestrator**. You do not apply rules yourself; you coordinate three sequential workers. Workers never write to disk — you do the final Write at the end, so the hooks run on the final, complete code (not on Worker 1's placeholder bodies or Worker 2's error-handling-free draft). This is a **process invariant, not a platform guarantee**: a `general-purpose` subagent inherits the project's `Write|Edit` PreToolUse hooks and *could* write if it ignored its brief, so the briefs forbid it (`Output JSON only`). If a worker writes prematurely, the hook simply blocks the incomplete code and you re-dispatch. If your host lets you restrict a subagent's tools, dispatch the workers without `Write`/`Edit`/`MultiEdit` to enforce this structurally.

## Worker roster

| Worker | Owns | Brief file |
|---|---|---|
| **Worker 1 — Structure & Architecture** | ST-*, OD-001, OD-002, OD-004, OD-005, DP-001 to DP-005, `<framework>/structure.md` | `workers/worker-1-structure.md` |
| **Worker 2 — Code Quality (line level)** | FN-001 to FN-009, NM-*, OD-003, FMT-* | `workers/worker-2-quality.md` |
| **Worker 3 — Failure Handling** | EH-*, FN-010 | `workers/worker-3-failure.md` |

Cross-cutting principles (DP-006 KISS, DP-007 DRY / FN-011 — the same idea in two families, and FN-012 "rewrite the draft, don't ship it") are applied **per-domain** by each worker as a lens — no single worker owns them. (FN-010, the idiomatic-failure-mechanism rule, is Worker 3's, not cross-cutting.)

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
  → Orchestrator runs hooks/review-files.py --json over the file set (deterministic pass)
  → Worker 1 outputs findings JSON (no code changes)
  → Worker 2 outputs findings JSON
  → Worker 3 outputs findings JSON
  → Orchestrator merges the linter findings + all worker findings, sorts by severity, presents unified report
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
     FRAMEWORK: <detected framework key from Step 1>
     MODE: write | review
     WORKER_<N-1>_OUTPUT: <previous worker's JSON, omit for Worker 1>
     ```
3. **Call the `Agent` tool** with:
   - `subagent_type: "general-purpose"`
   - `description: "coding-standards worker <N>"`
   - `prompt`: the constructed prompt
4. **Parse the worker's JSON output.** If parsing fails:
   - Retry once with a clarifying message: "Your previous response was not valid JSON. Return ONLY the JSON object specified in the brief."
   - If still failing, fall back to inline (load all references yourself, do the work, write files).
5. **Validate the output**:
   - Worker only modified files it had authority over (check `must_not_touch`).
   - Worker's `changes_made` / `decisions` / `error_handling_added` cite a rule code it owns.
   - Worker did not introduce abstractions outside its rule list (no new Strategy patterns from Worker 2; no new layers from Worker 3).
6. **If validation fails**, redispatch the worker with the specific violation noted. After one retry, fall back to inline.

> **TodoWrite (only if you seeded a list in SKILL.md Step 1.6):** mark worker N `in_progress` as you dispatch it and `completed` once its output validates (step 5 above). Tick the bracketing items the same way — the linter pass, and the final write-and-hooks (Write mode) or merge-and-present (Review mode) — as you reach each. If you didn't seed a list (TodoWrite unavailable, or inline single-file work), ignore this.

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

## After all workers complete (Review mode)

9. **Concatenate findings** from `hooks/review-files.py` (run it first — `--json` — these are deterministic must-fix) + Worker 1 + Worker 2 + Worker 3.
10. **Sort by severity** (must-fix → should-fix → consider) and group by file.
11. **Present** to the user as a structured PASS/FAIL table. Cite rule codes. Do not editorialize.

## Tell the user what happened

After the pipeline completes, summarize:

```
Worker 1 (Structure):
  - Placed 2 files per ST-001 capability layout
  - Designed Order as data structure (OD-002)
  - Wired DI per DP-005 — OrderService depends on PaymentGateway interface

Worker 2 (Quality):
  - Renamed 4 placeholders to intent-revealing names (NM-001)
  - Extracted 30-line function into 3 helpers (FN-001)
  - Fixed 1 Demeter chain (OD-003)

Worker 3 (Failure):
  - Added EH-002 boundary translation around stripe.charges.create
  - Awaited 1 floating Promise (EH-004)

Files written: <list>. Hooks passed.
```

## Pipeline invariants

- **Workers never call `Write`/`Edit`.** They emit code as JSON values. Only you (the orchestrator) write to disk.
- **Hooks fire on the orchestrator's final Write** per file, after Worker 3 — because workers emit JSON, not disk writes (a process invariant; see "The orchestrator's job" above). If a worker writes prematurely, the hook blocks the incomplete code and you re-dispatch.
- **No worker can modify rules outside its `owns_rules` list.** Validate before accepting output.
- **No retries past 2.** If a worker fails twice, fall back to inline.
- **Sequential, not parallel.** Worker N's output is Worker N+1's input. Do not dispatch Worker 2 before Worker 1 completes.
