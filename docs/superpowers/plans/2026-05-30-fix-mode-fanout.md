# Fix Mode (per-file fan-out) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third execution shape — **Fix mode** — that applies review findings across many files by fanning out one agent per file, tracked by a completeness ledger, so "fix everything" never silently stops half-done.

**Architecture:** Documentation/process change only (no code, no hooks). A new `MODE: fix` pipeline shape in `orchestrator-pipeline.md`; a new per-file specialist brief `workers/fix-agent.md`; mode routing in `SKILL.md`; a finding-ID note in `review-report.md`. The orchestrator still owns all writes (hooks fire once per file, unchanged).

**Tech Stack:** Markdown. The repo dogfoods its own hooks, so edits must pass them (markdown is exempt from the content hooks, but keep prose clean).

**Spec:** `docs/superpowers/specs/2026-05-30-fix-mode-fanout-design.md`

**Sequencing:** Land **after** the ST-008 plan (`2026-05-30-st-008-decomposition-rule.md`). Fix mode references ST-008 splits as a structural-fix category, so ST-008 should exist first. Same branch (`feat/st-008-decomposition-rule`) or a follow-up branch off it — see Task 0.

---

## Task 0: Branch decision

**Files:** none

- [ ] **Step 1: Confirm base**

```bash
cd "$(git rev-parse --show-toplevel)"
git branch --show-current
```
Expected: `feat/st-008-decomposition-rule` (continue on it — the two efforts ship together per the user's request), OR create `feat/fix-mode-fanout` off it if shipping as a separate PR:

```bash
# only if shipping separately:
git checkout -b feat/fix-mode-fanout
```

---

## Task 1: New `workers/fix-agent.md` brief

The per-file specialist. Receives one file + its findings, returns fixed content as JSON.

**Files:**
- Create: `skills/coding-standards/workers/fix-agent.md`

- [ ] **Step 1: Write the brief**

Create `skills/coding-standards/workers/fix-agent.md` with this content:

````markdown
---
worker: fix
name: per-file-fix-specialist
owns: applying a given list of review findings to ONE file
must_not_touch:
  - Any file other than the one in FILE_PATH
  - Findings not present in the FINDINGS input (no scope creep)
---

# Fix Agent — apply findings to a single file

You are a fix specialist in the coding-standards **Fix pipeline**. You fix **one
file**, guided by a specific list of findings. You see only this file — not the
rest of the project — so keep every change local to it.

## Inputs you receive

```
FILE_PATH:       <absolute path of the one file you fix>
CURRENT_CONTENT: <the file's current full content>
FINDINGS:        <JSON array; each: { id, rule, line, severity, fix } — ONLY this file's findings>
FRAMEWORK:       <detected framework key>
STRUCTURE:       <resolved project structure>
```

## What you do

1. For each finding in `FINDINGS`, apply the smallest change that satisfies the
   cited rule's `fix`. Apply the rule references the same way the rest of the skill
   does (common/ + framework). Do not invent fixes for things not in `FINDINGS`.
2. Keep the file compiling/coherent — if a finding's fix would break a reference
   that lives in another file (e.g. an exported name a barrel re-exports), make the
   *local* change and record the cross-file implication in the finding's `deferred`
   reason so the orchestrator can coordinate it. You never edit other files.
3. If you genuinely cannot fix a finding from this file alone (it needs a rename
   across files, a new shared module, a decision only the user can make), put it in
   `deferred` with a concrete reason. **Never silently drop a finding.**

## What you do NOT do

- Touch any other file.
- Address findings not in your `FINDINGS` list.
- Call `Write` / `Edit` — you emit JSON; the orchestrator writes the file so the
  hooks fire there.
- Reorganize or "improve" code beyond the findings (no scope creep, KISS).

## Output — JSON only, no prose

```json
{
  "path": "<FILE_PATH>",
  "fixed_content": "<the full new file content>",
  "fixed": ["<finding id>", "..."],
  "deferred": [{ "id": "<finding id>", "reason": "<why, concretely>" }]
}
```

Every finding id from `FINDINGS` MUST appear in exactly one of `fixed` or `deferred`.
````

- [ ] **Step 2: Verify the contract is self-consistent**

```bash
cd skills/coding-standards
grep -nE "fixed_content|deferred|must appear in exactly one" workers/fix-agent.md
```
Expected: the output schema and the "exactly one of fixed/deferred" invariant are present.

- [ ] **Step 3: Commit**

```bash
git add skills/coding-standards/workers/fix-agent.md
git commit -m "add fix-agent.md — per-file fix specialist brief"
```

---

## Task 2: Add the `MODE: fix` pipeline to `orchestrator-pipeline.md`

**Files:**
- Modify: `skills/coding-standards/references/orchestrator-pipeline.md`

- [ ] **Step 1: Add the Fix pipeline section**

After the "After all workers complete (Review mode)" section and before "Tell the user what happened", insert:

````markdown
## Fix mode (`MODE: fix`) — apply review findings at scale

Fix mode applies an existing review's findings across many files. It does **not**
run the Worker 1→2→3 sequence — the unit of independent work is a *file*, not a rule
domain — so it **fans out one fix-agent per file**. This is the path that scales: a
large finding set *triggers* fan-out instead of overflowing one context.

**Input:** the most recent `.coding-standards/reviews/<ts>.md` report (or an
in-session review's findings). If none exists, run Review first to produce one.

1. **Build the completeness ledger.** One row per finding:
   `{ id, file, line, rule, severity, status }`, `status = pending`. The id is the
   per-finding id from the review report (see `references/review-report.md`).

2. **Partition findings:**
   - **STRUCTURAL / cross-file** — ST-002 (barrels/`index`), ST-003 (deep imports),
     ST-008 (file splits), moves/renames. These have ordering dependencies.
   - **FILE-LOCAL** — FN-*, NM-*, EH-*, FMT-*, OD-003. Independent per file.

3. **Phase A — structural, coordinated.** Do these yourself (orchestrator), in order,
   because later steps depend on earlier ones:
   a. create/extend barrel `index` files (ST-002);
   b. rewrite deep imports to the new public entries (ST-003);
   c. apply ST-008 splits (create named sibling files, move declarations).
   Each write goes through the orchestrator, so the hooks fire. Update the ledger.
   Independent barrels may fan out, but an import rewrite runs only after the barrel
   it targets exists.

4. **Phase B — file-local, fan-out (parallel, one agent per file).** For each file
   that still has file-local findings, dispatch `workers/fix-agent.md` via the
   `Agent` tool (`subagent_type: "general-purpose"`), batched to the host's
   concurrency cap. The agent's INPUT carries **only that file's current content and
   its own findings** — never the whole set. Parse the returned JSON
   (`{ path, fixed_content, fixed[], deferred[] }`), then **you** write the file
   (hooks fire per file). Update the ledger: each finding → `fixed` or
   `deferred(reason)`.

5. **Verify.** Run `hooks/review-files.py --json` over every changed file. If a
   finding that was marked `fixed` still trips the linter, flip it to `pending` and
   re-dispatch that one file (max **2** re-fix passes per file; then
   `deferred(reason="re-fix failed")`).

6. **Report against the ledger.** State `N of M findings fixed across K files; D
   deferred`, and **list every deferred finding with its reason**. An incomplete run
   says exactly what remains and why — it never stops silently.

**Fallback when `Agent` is unavailable** (Cursor/Codex/OpenCode): run Phases A and B
yourself in batches, one file at a time, still driven by the ledger, and report the
same way. Announce that fan-out is unavailable in this host.
````

- [ ] **Step 2: Add Fix invariants**

In the `## Pipeline invariants` list at the end of the file, append:

```markdown
- **Fix mode fans out by file, not by rule domain.** One fix-agent per file, each
  given only that file's content + its findings. Structural (cross-file) fixes run
  first, coordinated by the orchestrator; file-local fixes fan out in parallel.
- **Fix mode is ledger-complete.** Every finding ends `fixed` or `deferred(reason)`;
  a silent partial result is a failure. Max 2 re-fix passes per file.
```

- [ ] **Step 3: Verify**

```bash
cd skills/coding-standards
grep -nE "MODE: fix|fan-out|completeness ledger|fix-agent" references/orchestrator-pipeline.md | head
```
Expected: the Fix section, ledger, and fix-agent references are present.

- [ ] **Step 4: Commit**

```bash
git add skills/coding-standards/references/orchestrator-pipeline.md
git commit -m "orchestrator-pipeline: add MODE: fix per-file fan-out shape"
```

---

## Task 3: Route Fix mode in `SKILL.md`

**Files:**
- Modify: `skills/coding-standards/SKILL.md`

- [ ] **Step 1: Locate the mode-routing points**

```bash
cd skills/coding-standards
grep -nE "Write mode|Review mode|Step 0.5|Step 1.5|Step 1.6|Mode: Write vs Review" SKILL.md | head
```
Note the line numbers for the edits below.

- [ ] **Step 2: Add Fix to the "Mode: Write vs Review" section**

Rename the section heading `## Mode: Write vs Review` to `## Mode: Write, Review, or Fix` and, after the Review mode subsection, add:

````markdown
### Fix mode

When the user says **"fix the findings"**, **"apply the review"**, **"fix everything
from the review"**, or asks for fixes right after a Review, you are in **Fix mode** —
apply an existing review's findings across the affected files.

Fix mode **always runs as the orchestrator pipeline** (`MODE: fix`) because it is
inherently multi-file: it fans out one fix-agent per file, tracked by a completeness
ledger so nothing is silently half-fixed. **Do not** offer a "single agent" option
for Fix. If the `Agent` tool is unavailable in this host, run the documented
sequential-batch fallback and say so.

The full Fix pipeline — ledger, structural-vs-file-local partition, per-file fan-out,
verify, and ledger-based report — is in `references/orchestrator-pipeline.md` under
"Fix mode (`MODE: fix`)". Read it before dispatching. The input is the most recent
`.coding-standards/reviews/<ts>.md` report; if none exists, run Review first.
````

- [ ] **Step 3: Add the Fix trigger to Step 0.5 routing**

In Step 0.5, where the three picker outcomes are listed ("Write code…", "Check existing code…", "Show me the rules"), add a routing note after them:

```markdown
- **Fix existing code from a review** (user says "fix the findings" / "apply the
  review") → this is **Fix mode**: skip the Write/Review picker, go to Step 1 (detect
  framework per file in the finding set) → Step 1.4 (resolve structure) → run the
  `MODE: fix` orchestrator pipeline (`references/orchestrator-pipeline.md`). Fix mode
  does not ask the Step 1.5 run-mode question — it is always the pipeline.
```

- [ ] **Step 4: Note Fix in Step 1.5**

In Step 1.5, add a row/line stating that Fix tasks always use the orchestrator pipeline and skip the run-mode question:

```markdown
| Task = apply review findings ("fix the findings" / "apply the review") | **Orchestrator pipeline, `MODE: fix`, always.** Per-file fan-out; no run-mode question. Falls back to sequential batches if `Agent` is unavailable. |
```

- [ ] **Step 5: Add a Fix task-list shape to Step 1.6**

In Step 1.6, after the Review shapes, add:

```markdown
**Fix — orchestrator pipeline (apply review findings):**
1. Load findings + build the completeness ledger
2. Partition: structural (cross-file) vs file-local
3. Phase A — structural fixes (barrels, deep imports, ST-008 splits)
4. Phase B — fan out one fix-agent per file (parallel)
5. Verify (re-run review-files.py) + report against the ledger
```

- [ ] **Step 6: Verify**

```bash
cd skills/coding-standards
grep -nE "Fix mode|MODE: fix|fix the findings|completeness ledger" SKILL.md | head
```
Expected: Fix mode appears in the Mode section, Step 0.5, Step 1.5, and Step 1.6.

- [ ] **Step 7: Commit**

```bash
git add skills/coding-standards/SKILL.md
git commit -m "SKILL.md: route 'fix the findings' to MODE: fix orchestrator pipeline"
```

---

## Task 4: Finding IDs in `review-report.md` (the ledger key)

Fix mode's ledger tracks findings by a stable id. Ensure the review report assigns one.

**Files:**
- Modify: `skills/coding-standards/references/review-report.md`

- [ ] **Step 1: Check whether findings already have stable ids**

```bash
cd skills/coding-standards
grep -niE "\bid\b|finding[- ]?id|F[0-9]|numbered" references/review-report.md | head
```

- [ ] **Step 2: Add a finding-id convention if absent**

If the report format does not already give each finding a stable id, add a short
subsection to `references/review-report.md`:

```markdown
## Finding IDs (used by Fix mode)

Each finding gets a stable id within the report: `F<NNN>` numbered in document order
(`F001`, `F002`, …). Fix mode's completeness ledger keys on these ids, so every
finding can be tracked to `fixed` or `deferred`. Keep ids stable for the life of the
report file — never renumber after the report is written.
```

If ids already exist under another name, instead add one line noting that Fix mode
keys its ledger on that existing id field, and skip the new subsection.

- [ ] **Step 3: Verify + commit**

```bash
cd skills/coding-standards
grep -niE "Fix mode|finding id|F<NNN>|F001" references/review-report.md | head
git add skills/coding-standards/references/review-report.md
git commit -m "review-report: stable finding IDs for the Fix-mode ledger"
```

---

## Task 5: Dogfood + coherence verification

**Files:** none

- [ ] **Step 1: Lint every touched file with the skill's own review driver**

```bash
cd skills/coding-standards
python3 hooks/review-files.py \
  workers/fix-agent.md references/orchestrator-pipeline.md SKILL.md \
  references/review-report.md
```
Expected: no must-fix violations (markdown is exempt from content hooks; this confirms nothing trips them).

- [ ] **Step 2: End-to-end coherence read**

Confirm the three references agree on the contract (no drift):

```bash
cd skills/coding-standards
echo "fix-agent output schema:"; grep -E "fixed_content|fixed\"|deferred" workers/fix-agent.md
echo "pipeline expects same:";   grep -E "fixed_content|fixed\[\]|deferred" references/orchestrator-pipeline.md
echo "SKILL routes to it:";      grep -E "MODE: fix" SKILL.md
```
Expected: the fix-agent's `{ path, fixed_content, fixed[], deferred[] }` matches what the pipeline says it parses; SKILL.md points at `MODE: fix`. Fix any mismatch (the schema is the single source of truth — `workers/fix-agent.md`).

- [ ] **Step 3: Spec coverage check**

```bash
cd skills/coding-standards
for k in "MODE: fix" "completeness ledger" "fan out" "fix-agent" "deferred"; do
  printf "%-22s " "$k:"; grep -rl "$k" SKILL.md references/orchestrator-pipeline.md workers/fix-agent.md | tr '\n' ' '; echo
done
```
Expected: every concept appears in at least one file; ledger + fan-out + deferred appear in both SKILL.md/pipeline.

- [ ] **Step 4: Final state**

```bash
git log --oneline | head -8
git status
```
Expected: Task 1-4 commits present; clean tree.

---

## Self-review notes (author check — completed)

- **Spec coverage:** pipeline shape → Task 2; fix-agent brief → Task 1; SKILL routing (0.5/1.5/1.6/Mode) → Task 3; finding-id ledger key → Task 4; dogfood → Task 5. All spec sections mapped.
- **Contract consistency:** the fix-agent output `{ path, fixed_content, fixed[], deferred[] }` is defined once (Task 1) and referenced identically in Tasks 2 and 5; the ledger statuses `fixed` / `deferred(reason)` and "max 2 re-fix passes" are consistent across pipeline + SKILL + invariants.
- **No placeholders:** every step shows the actual markdown to insert and the verification command + expected output.
- **Out of scope (per spec):** ST-008 rule/hook (prior plan), changing Review's report content beyond adding a stable id, parallelizing Phase A beyond safe ordering — none appear here.
