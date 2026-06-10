# Fix plan file (milestone ledger)

A milestone-driven fix run (`orchestrator-pipeline.md` → Fix mode) persists its plan and progress to a Markdown file so the run survives session bloat, compaction, and restarts. The file — not the conversation — is the source of truth for what is fixed, pending, or deferred. Chat shows one status line per milestone; this file holds everything else.

## Path + lifecycle

1. Path: `<root>/.coding-standards/fixes/<review-ts>.md`, where `<review-ts>` is the timestamp of the source review report (`.coding-standards/reviews/<review-ts>.md`) — a 1:1 link, **not** a new timestamp. Create `.coding-standards/fixes/` if absent.
2. Created at fix start, with the approved scope, **before any write to user code**.
3. Gitignored via the `.coding-standards/` line (the review that produced the source report already ensured it — see `review-report.md`) and excluded from future reviews the same way as reports (`hooks/_exclusions.py`).
4. Rewritten in full (replace the whole file, don't patch single lines) **immediately after each milestone verifies**, before the chat status line. A crash therefore loses at most one milestone's ledger update — resume's re-verify reconciles it.
5. Timestamps come from the shell (`date +%Y-%m-%d-%H%M%S`), never from the agent.

## File shape

```markdown
# Fix plan — from reviews/2026-06-02-141503.md

- **Source report:** .coding-standards/reviews/2026-06-02-141503.md
- **Scope:** all findings (no severity tiers — every finding is in scope)
- **Commit policy:** commit per milestone (tree clean at start: yes)
- **Approved:** 2026-06-02-142010
- **Status:** in_progress (M3 of 4)

## M1 — structural — done — commit a1b2c3d
- [x] F004 — src/auth/index.ts — ST-002 — add barrel
- [x] F011 — src/billing/invoice.ts:3 — ST-003 — rewrite deep import

## M2 — src/auth (5 findings) — done-with-open-breaches — commit d4e5f6a
- [x] F001 — src/auth/login.ts:42 — FN-005 — group args into options object
- [ ] F002 — src/auth/session.ts:18 — DP-001 — **accepted: one cohesive state machine; methods share private session state, no clean seam**
- [ ] F003 — src/auth/token.ts — DP-007 — **deferred (OPEN BREACH): refresh logic duplicated in billing/; shared home needs a cross-team decision**

## M3 — src/billing (8 findings) — in_progress
- [ ] F015 — src/billing/invoice.ts:77 — NM-003 — rename Hungarian prefix

## M4 — src/payments (4 findings) — pending
- [ ] F021 — src/payments/checkout.ts:12 — FN-002 — extract function

## Follow-ups (not in scope)
- promote: src/notifications/ — email-sender, sms-sender, push-sender share a theme (3+ flat siblings) → sub-feature folder earned
```

## Statuses

- **Milestone:** `pending` → `in_progress` → `done` | `done-with-open-breaches`.
- **Finding terminal states — exactly one, and `fixed` is reserved for a removed violation:**
  - `fixed` — checkbox `[x]`. The violation is **gone**, verified (re-run `review-files.py` for mechanical findings; the reviewer confirms for judgement findings). A cosmetic change that leaves the violation is NOT `fixed`.
  - `accepted` — unchecked `[ ]` + bold `**accepted: <reason>**`. Reviewed and judged **not a real violation** here (rule N/A, genuinely cohesive, proxy false positive). Closes clean; the reason must name *why* it isn't a violation — `by design` alone is not a reason.
  - `deferred` — unchecked `[ ]` + bold `**deferred (OPEN BREACH): <reason>**`. A **real violation deliberately not fixed** this pass. An open breach, not a closed item.
  - `pending` — unchecked `[ ]`, plain. Not yet reached.
  - Finding IDs are the report's `F<NNN>` ids — never renumber or drop them.
- **Header `Status:`** — `in_progress (M<k> of <total>)` while looping; `blocked (M<k>: <reason>)` when stopped. Terminal:
  - `done` — every in-scope finding ended `fixed` or `accepted`. **No `deferred` (open-breach) findings remain.**
  - `done-with-open-breaches (<D> unresolved)` — finished but `D` real violations were deferred. NOT `done`. The final report lists every one and asks the user to resolve each (fix later / accept with reason / explicitly waive). `done` may only print after the user resolves them.

## Follow-ups

Work the run *discovered* but must not *do*. Phase-A step d (`orchestrator-pipeline.md`, Fix mode) records promotion candidates here — folders whose flat siblings crossed ST-008's Rule of Three after the splits landed. Entries are outside the approved scope: never executed during the run, never blocking a milestone, surfaced as one-line offers in the final report. The section is omitted when there are no candidates.

## Resume procedure

Triggered by "continue the fix" / "resume the fix", or by Fix mode finding a non-done plan for the requested report.

1. Find the newest `.coding-standards/fixes/*.md` whose header `Status:` is not terminal (`done` / `done-with-open-breaches`). A `blocked` plan IS resumable: surface the recorded blocker reason first and resolve it — if it needs a user decision, ask that one question (the recorded blocker is the sole exception to no-repeated-questions).
2. For any milestone marked `in_progress`, re-run `hooks/review-files.py --json` over that milestone's files and reconcile: a finding that no longer trips and whose fix is visibly applied → check it; a finding still tripping → leave pending. (Crash protection — a write may have landed without its ledger update.)
3. Continue the milestone loop from the first non-done milestone. **No re-approval, no repeated questions** — the header records the original approval and scope.

## Invariants

- Disk is the source of truth; harness task lists (`TaskCreate`/`TodoWrite`) only mirror it and are never read back as state.
- Every finding in approved scope ends `fixed`, `accepted`, or `deferred` (with reason) — the same ledger-completeness rule as the single-pass fix. Silence is failure.
- **`fixed` means the violation is gone — not "touched".** Trimming a god class by 30 lines, or renaming around a duplication, is `accepted` (genuinely not a violation) or `deferred` (it is) — never `fixed`. "Done" must reflect the standard, not the diff.
- **A god-class / SRP concern is its own finding.** When a file trips only the ST-008 *size* advisory but the reviewer suspects DP-001, raise an explicit DP-001 finding and adjudicate it. Never let "size advisory, by design" stand in for an unmade SRP judgement.
