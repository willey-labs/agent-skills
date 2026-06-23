# Review report file

Every review — orchestrator pipeline *and* inline single-agent — persists its merged result to a Markdown file so it's durable, diffable, and feedable to a later fix pass. The same content is also printed to the user — except above the scope threshold (defined once in `orchestrator-pipeline.md` → Fix mode), where chat gets the Summary line, the first ~20 findings, the remaining-count, and the report path, and the full table lives here only. The file is always complete either way.

There are **no severity tiers** — every finding is a violation to fix. The report is one ordered findings table, not a must-fix/should-fix/consider split. A finding's only non-fix exit is at Fix time: `accepted` (reviewer judged it is not a violation — reason required) or `deferred` (open breach).

## Procedure

1. **Resolve the repo root** — the nearest ancestor with `.git` / `package.json` / `pyproject.toml` / `go.mod` / `composer.json` / `pom.xml` / etc. (the same marker walk as `hooks/_exclusions.py:find_project_root`).
2. **Compute a timestamp** — run `date +%Y-%m-%d-%H%M%S` (the shell, not the agent, supplies the time). Name the file `<root>/.coding-standards/reviews/<timestamp>.md`. Create `.coding-standards/reviews/` if absent.
3. **Ensure it's gitignored** — if `<root>/.gitignore` doesn't already contain a `.coding-standards/` line, append one (create `.gitignore` if absent). Idempotent; announce it the first time only.
4. **Write the report** in the shape below.
5. **Tell the user the path** at the end of the review.

The config files `.coding-standards-structure` and `.coding-standards-ignore` stay **flat at the framework project root** (the sub-project root in a monorepo) — they are not under `.coding-standards/`. Only generated review artifacts live in the directory, which is why ignoring the whole directory is safe.

The report file is excluded from future reviews — `**/.coding-standards/**` is in the default exclusion list (`hooks/_exclusions.py`) — so a review never reviews a past review.

## Report shape

```markdown
# Coding-standards review — <timestamp>

- **Scope:** <files reviewed>
- **Framework:** <framework>
- **Structure baseline:** <exactly one of the three forms below>
- **Run mode:** orchestrator pipeline | inline

## Summary
findings: N (all must-fix) — <rules passed> passed, <rules skipped> skipped (n/a)

## Findings
| ID | File:Line | Rule | Issue | Fix |
|---|---|---|---|---|
| F001 | … | … | … | … |

## Coverage
- **Passed:** <rule codes that applied and were clean>
- **Skipped (n/a):** <rule code — why>
```

Findings are ordered by **file, then line, then rule code** — no severity grouping. A clean review still writes the table with a single `_none_` row, and the Coverage section is the comprehensiveness signal: it shows every rule was checked (passed/skipped), not quietly dropped.

## The `Structure baseline` field is mandatory and self-describing

Structural findings only mean something measured against a recorded structure (SKILL.md Step 4). The field records which one — in **exactly one** of three forms, and it names the file on disk so the claim is verifiable:

```markdown
- **Structure baseline:** follows feature-first — recorded at `.coding-standards-structure`
- **Structure baseline:** custom — recorded at `apps/web/.coding-standards-structure`
- **Structure baseline:** NOT RECORDED — structural review not grounded (<reason>)
```

The first two assert a recorded structure and **must** name the `.coding-standards-structure` file (the sub-project path in a monorepo). The third is the only legitimate way to omit a baseline, and only for a stated reason — an unsupported framework, or a below-threshold review that declined comprehension. There is no fourth form: a report that names a structure without a file behind it, or omits the field, is not a valid report.

**Verify before reporting done.** After writing the report, run the field against disk:

```bash
python3 <skill-dir>/hooks/check-review-report.py <report.md> [--root <framework-project-root>]
```

Exit `0` grounded (file present), `1` declared skip (surface the reason to the user), `2` inconsistent — the field claims a structure with no file, or is missing. On `2`, the structure step was skipped: resolve + record it (Step 4), then rewrite the report. This is the deterministic back-stop for the task-list item — the report can't read as complete while asserting a baseline that was never written.

## Finding IDs (used by Fix mode)

Each finding gets a stable id within the report: `F<NNN>` numbered in document order
(`F001`, `F002`, …), emitted in the leading `ID` column of the findings table. IDs
are unique across the whole report (not reset per section). Fix mode's completeness
ledger keys on these ids, so every finding can be tracked to `fixed` or `deferred`.
Keep ids stable for the life of the report file — never renumber after the report is
written. A milestone-driven fix persists that ledger as a plan file —
`.coding-standards/fixes/<review-ts>.md`, same timestamp as this report — see
`references/fix-plan.md`.
