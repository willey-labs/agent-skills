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
- **Scope:** must-fix + should-fix (consider: excluded)
- **Commit policy:** commit per milestone (tree clean at start: yes)
- **Approved:** 2026-06-02-142010
- **Status:** in_progress (M3 of 4)

## M1 — structural — done — commit a1b2c3d
- [x] F004 — src/auth/index.ts — ST-002 — add barrel
- [x] F011 — src/billing/invoice.ts:3 — ST-003 — rewrite deep import

## M2 — src/auth (5 findings) — done-with-deferrals — commit d4e5f6a
- [x] F001 — src/auth/login.ts:42 — FN-005 — group args into options object
- [ ] F002 — src/auth/session.ts:18 — EH-002 — **deferred: re-fix failed after 2 passes**

## M3 — src/billing (8 findings) — in_progress
- [ ] F015 — src/billing/invoice.ts:77 — NM-003 — rename Hungarian prefix

## M4 — src/payments (4 findings) — pending
- [ ] F021 — src/payments/checkout.ts:12 — FN-002 — extract function
```

## Statuses

- **Milestone:** `pending` → `in_progress` → `done` | `done-with-deferrals`.
- **Finding:** checked = fixed; unchecked with a bold `**deferred: <reason>**` suffix = deferred; unchecked plain = pending. Finding IDs are the report's `F<NNN>` ids — never renumber or drop them.
- **Header `Status:`** mirrors the run: `in_progress (M<k> of <total>)` while looping; `done` / `done-with-deferrals` when every milestone is terminal; `blocked (M<k>: <one-line reason>)` when a blocker stopped the run.

## Resume procedure

Triggered by "continue the fix" / "resume the fix", or by Fix mode finding a non-done plan for the requested report.

1. Find the newest `.coding-standards/fixes/*.md` whose header `Status:` is not terminal (`done` / `done-with-deferrals`). A `blocked` plan IS resumable: surface the recorded blocker reason first and resolve it — if it needs a user decision, ask that one question (the recorded blocker is the sole exception to no-repeated-questions).
2. For any milestone marked `in_progress`, re-run `hooks/review-files.py --json` over that milestone's files and reconcile: a finding that no longer trips and whose fix is visibly applied → check it; a finding still tripping → leave pending. (Crash protection — a write may have landed without its ledger update.)
3. Continue the milestone loop from the first non-done milestone. **No re-approval, no repeated questions** — the header records the original approval and scope.

## Invariants

- Disk is the source of truth; harness task lists (`TaskCreate`/`TodoWrite`) only mirror it and are never read back as state.
- Every finding in approved scope ends checked or deferred-with-reason — the same ledger-completeness rule as the single-pass fix. Silence is failure.
