# Review report file

Every review — orchestrator pipeline *and* inline single-agent — persists its merged result to a Markdown file so it's durable, diffable, and feedable to a later fix pass. The same content is also printed to the user; the file is an additional artifact, not a replacement for the chat summary.

## Procedure

1. **Resolve the repo root** — the nearest ancestor with `.git` / `package.json` / `pyproject.toml` / `go.mod` / `composer.json` / `pom.xml` / etc. (the same marker walk as `hooks/_exclusions.py:find_project_root`).
2. **Compute a timestamp** — run `date +%Y-%m-%d-%H%M%S` (the shell, not the agent, supplies the time). Name the file `<root>/.coding-standards/reviews/<timestamp>.md`. Create `.coding-standards/reviews/` if absent.
3. **Ensure it's gitignored** — if `<root>/.gitignore` doesn't already contain a `.coding-standards/` line, append one (create `.gitignore` if absent). Idempotent; announce it the first time only.
4. **Write the report** in the shape below.
5. **Tell the user the path** at the end of the review.

The config files `.coding-standards-structure` and `.coding-standards-ignore` stay **flat at the repo root** — they are not under `.coding-standards/`. Only generated review artifacts live in the directory, which is why ignoring the whole directory is safe.

The report file is excluded from future reviews — `**/.coding-standards/**` is in the default exclusion list (`hooks/_exclusions.py`) — so a review never reviews a past review.

## Report shape

```markdown
# Coding-standards review — <timestamp>

- **Scope:** <files reviewed>
- **Framework / structure:** <framework> / <resolved structure>
- **Run mode:** orchestrator pipeline | inline

## Summary
must-fix: N · should-fix: N · consider: N — <rules passed> passed, <rules skipped> skipped (n/a)

## must-fix
| ID | File:Line | Rule | Issue | Fix |
|---|---|---|---|---|
| F001 | … | … | … | … |

## should-fix
| ID | File:Line | Rule | Issue | Fix |

## consider
| ID | File:Line | Rule | Issue | Fix |

## Coverage
- **Passed:** <rule codes that applied and were clean>
- **Skipped (n/a):** <rule code — why>
```

A section with no findings still appears, with a single `_none_` row — the empty sections are part of the comprehensiveness signal (they show the severity was checked, not skipped).

## Finding IDs (used by Fix mode)

Each finding gets a stable id within the report: `F<NNN>` numbered in document order
(`F001`, `F002`, …), emitted in the leading `ID` column of each severity table. IDs
are unique across the whole report (not reset per section). Fix mode's completeness
ledger keys on these ids, so every finding can be tracked to `fixed` or `deferred`.
Keep ids stable for the life of the report file — never renumber after the report is
written.
