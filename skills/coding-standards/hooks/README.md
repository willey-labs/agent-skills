# coding-standards hooks

PreToolUse hooks that hard-block Write/Edit/MultiEdit when high-precision
violations are detected. The agent sees the block as a tool error and must
fix the violation before retrying — that's the enforcement. Where a rule's
signal is real but not precise enough to block (raw file size, print residue,
comment prose), the hook exits 0 and reports an advisory instead — still a
must-fix violation, just adjudicated rather than refused.

## Hooks shipped

| Hook | Scope | What it catches |
|---|---|---|
| `block-junk-paths.py` | All languages (path-only; Write/Edit/MultiEdit) | ST-005 junk-drawer filenames (`utils.ts`, `helpers.py`, `common.go`, ...) **and folders** (a source file under `utils/`/`helpers/`/`common/`/`misc/`); ST-005 corollary top-level mega-files (`src/types.ts`, `src/constants.ts`, ...) |
| `block-ts-violations.py` | `.ts .tsx .mts .cts .js .jsx .mjs .cjs .vue .svelte` | `any` (annotation, `as`/`satisfies`, `[]`, generic arg in any position incl. `Record<string, any>`, `type X = any`, `extends any`); NM-006 Hungarian (incl. class fields / interface members / object properties); ST-003 deep imports; parent traversal. For `.vue`/`.svelte`, `<script>` blocks are extracted and checked (regex + AST), line numbers aligned to the SFC. **AST checks (required — bootstrap installs tree-sitter):** FN-001 function length, FN-005 precise arg count (4+; exempts DI parameter-property constructors + the Express error-middleware shape), OD-004 hybrid class detection (OD-005 framework-boundary carve-out). Regex-only is a defensive fallback if the grammars are ever absent. |
| `block-py-violations.py` | `.py .pyi` | `typing.Any` (annotation, subscript in any position incl. PEP 585 `dict[str, Any]`, PEP 604 `int | Any`, `cast(Any, …)`); NM-006 Hungarian snake_case; `from x import *`. **AST checks (always on — stdlib `ast`):** FN-001 function length, FN-005 precise arg count (5+ — Python has named args; exempts FastAPI bindings as `Depends()`/`Query()` defaults AND `Annotated[…, Depends()]` annotations, plus test functions / `@pytest.fixture`), OD-004 hybrid class detection with OD-005 framework-boundary carve-out (Model, BaseModel, Serializer, Form, etc.). |
| `block-go-violations.py` | `.go` | `interface{}` / `any` (param/return/var/return-tuple/`map[K]any`/`map[any]V`/slice); NM-006 Hungarian (`strName`, multi-char prefixes; decl/short-var/param shapes); FN-005 4+ params (multi-line joined; `New*` constructor functions exempt); `import . "fmt"` dot imports |
| `block-csharp-violations.py` | `.cs` | `dynamic` (var/list/dict); NM-006 Hungarian (`strName`, `m_field`, ...); FN-005 5+ params (named-arg language; records + constructors exempt; multi-line joined) |
| `block-php-violations.py` | `.php` | `mixed` type; NM-006 Hungarian (`$strName`, ...); FN-005 4+ params (`__construct` exempt; multi-line joined) |
| `block-jvm-violations.py` | `.java .kt .kts` | Star imports (`import com.foo.*`); NM-006 Hungarian (`strName`, multi-char prefixes; Java `Type strName` + Kotlin `val/var`/param shapes); FN-005 4+ params Java / 5+ Kotlin (records + Java constructors exempt; multi-line joined); Kotlin `Any` (annotation/generic) |
| `block-swallowed-errors.py` | `.ts .tsx .js .jsx .mts .cts .mjs .cjs .vue .svelte .py .pyi .go .cs .java .kt .kts .php` | EH-002 swallowed errors: empty `catch (e) {}` / `catch {}` and empty `.catch(() => {})` (brace langs), Go `_ = err` and empty `if err != nil {}`, Python `except …: pass` / `: ...`. Runs on RAW text — a comment inside the block (the documented EH-002 escape) means it isn't empty and is allowed. |
| `block-debug-artifacts.py` | same language set as swallowed-errors | FMT-005. **Blocks (exit 2)** debugger/halt forms never meant to ship: `debugger` (JS/TS), `breakpoint()`/`pdb.set_trace()`/`import pdb` (Python), `dd()`/`var_dump()` (PHP). **Advises (exit 0)** print-style residue (`console.log`, `print(`, `fmt.Print*`, `Console.WriteLine`, `System.out.print`, Kotlin `println`) and commented-out code — these have legit uses (CLI/logger/explanatory comment), so they're flagged to confirm, not blocked. Residue patterns run on string/comment-stripped text; the commented-code check on raw lines. |
| `block-god-file.py` | All source languages | ST-008, both directions. **Blocks (exit 2)** when a non-test/non-schema source file has more than 10 *behavioral* top-level declarations (functions/classes/methods) — the least-blunt proxy for "does many jobs" (a data-only file of consts/types/enums has zero, so it never blocks; a 1.7k-line single class is one, so length alone never blocks). Strings/comments are stripped before the count, so a file embedding code samples isn't miscounted. **Advises (exit 0)** on raw size (> 400 lines) and flat-folder promotion (a NEW source file landing in a folder already past 12 flat source units — 3+ themed siblings have earned a sub-feature folder, Rule of Three). Also **advises (exit 0)** on over-long function bodies (FN-001) for the languages with no AST statement-count — Go, C#, Java, Kotlin, PHP (a blunt brace-matched line count, generous threshold, so it warns rather than blocks; TS/JS/Python get the precise AST block instead). Thresholds are fixed by the standard — no per-project tuning. Skips test, schema, fixture, story, and excluded/generated files. |
| `advise-comment-slop.py` | Every source language (comments + Python docstrings) | CM-004/CM-005/CM-006, **advisory only (exit 0, findings delivered as tool-result context, never exit 2)**. The mechanical comment tells: emoji or an exclaimed comment; edit narration (`// NEW:`, a sentence about what an edit did, a was/now pair); history narration (`used to be`, `no longer needed`); filler preambles (`Note:`, `Basically`, `Here's how this works`); banner/divider comments; reader address (`as requested`, `let me know`); first-person deliberation (`I think`, `I've kept`); deliberation left in place (`we could also`, `not sure if`); `TODO`/`FIXME` with no ticket or link. Prose can't be hard-blocked at the ~1% false-positive bar, so the judgement calls (is this narration? does the docstring add anything?) stay in review. String literals are blanked first, so a `#` in a JS string is never read as a comment; `#` counts as a comment marker only where the language says so; linter pragmas, shebangs and SPDX lines are exempt. Capped at 15 findings per file. |
| `block-added-comments.py` | Every source language (comments + Python docstrings) | CM-007 one line or none. **Blocks (exit 2)** any comment block the write *adds* that runs past one line of prose — past one line a comment has stopped stating the constraint and started arguing the decision. Only added prose is judged: the file on disk is read first and its existing comment lines subtracted, so re-writing a file or editing beside an old paragraph passes. Judging whole files instead would refuse roughly a third of the comment blocks in a mature codebase, most of them load-bearing — which is why the file-on-disk subtraction is what makes this a hard block rather than an advisory. A block opening the written text (first two lines) is exempt, so file-header docstrings pass; machine pragmas are exempt anywhere. Limit overridable with `CODING_STANDARDS_MAX_COMMENT_LINES`. Capped at 10 findings per file. |
| `block-structure-file-violations.py` | `.coding-standards-structure`, `.coding-standards-ignore` | Guards the config dotfiles. Structure file: **blocks (exit 2)** a comment line, a `hooks:` block, or any legacy rule toggle; allows `follows:` / `layout:`. Ignore file: **blocks** any exemption pattern lacking a trailing `# reason: …`, and emits a loud advisory naming every added exemption (no silent self-exemption). |

## The comment judge — two more events

Comment prose is the one rule family a regex can't settle, and the pass that wrote a
comment is the worst judge of whether it earns its place. So two hooks run outside
PreToolUse:

| Hook | Event | What it does |
|---|---|---|
| `inject-coding-standards.py` | `SessionStart` (`startup`) + `UserPromptSubmit` (no matcher) | Prints the comment default, CM-007, and the write-through-tools rule to stdout, which both events add to Claude's context. Carries the rules enforcement cannot recover once missed: a refused write costs a whole turn, and a file written by shell redirection reaches no hook at all. Never exits non-zero — a non-zero `UserPromptSubmit` hook would block the user's prompt. |
| `record-touched-files.py` | `PostToolUse` on `Write|Edit|MultiEdit` | Notes each source file a turn wrote in a per-session ledger under the user's data dir (never in the repo). Excluded, generated and non-source files are skipped, so no model call is ever spent on code the standard doesn't govern. |
| `judge-comments.py` | `Stop` (no matcher) | Collects the comments on lines the turn changed, sends them with the CM rules to a **separate** `claude -p` call (one turn, no tools, no MCP, no hooks), and on a delete or shorten verdict exits 2 — which the hook contract turns into "prevents Claude from stopping", with the findings fed back as the fix to apply. Trimming a comment can't change behaviour, so the fix needs no approval; a verdict that is genuinely wrong may be kept with the reason stated. |

Cost and bounds: one short model call per turn that wrote source files, and none when
those files gained no comments. The judge model defaults to `sonnet`, overridable with
`CODING_STANDARDS_JUDGE_MODEL`. A session is held open at most twice; after that
findings are reported and the turn ends. Every failure path — no CLI on PATH, a failing
call, a timeout, an answer that isn't JSON, an already-active Stop hook, our own nested
call — exits 0. A judge that breaks must not be able to block work.

Only lines the working tree changed are judged, so a legacy file's existing comments
are never dragged in. Where that can't be determined (not a repo, or the change is
already committed), a file is judged whole only while it carries few comments.

### What runs on every Write/Edit/MultiEdit

All hooks run on each call. Each one checks the file extension first and
exits 0 cleanly if the file doesn't match its language.

`block-junk-paths.py` is path-based and fires on `Write`, `Edit`, and
`MultiEdit` — a junk-drawer name is a violation however the file got there, so
the next edit to an existing `utils.ts` is blocked until it's renamed (use
`.coding-standards-ignore` for a legacy file you're not ready to rename).

## Review mode — run the hooks as a linter (read-only)

The hooks above are **write-time**: they fire on `Write`/`Edit`/`MultiEdit`. A
code *review* writes nothing, so they don't fire on their own. To get the same
deterministic checks while reviewing existing files, run the bundled driver:

```bash
python3 review-files.py <file> [<file> ...]
git diff --name-only | python3 review-files.py --stdin
python3 review-files.py --json <file> ...     # machine-readable, for the orchestrator
```

It feeds each file's current content to every content hook as a synthetic
`Write` payload — identical to the write-time contract — and prints the
violations grouped by file. Excluded files are skipped exactly as at write time.
It always exits `0` (it reports; it never blocks). The skill's Review mode runs
this as its final deterministic pass — after the judgement pass / specialist
workers — and merges the findings in. Every finding is a violation to fix; there are no severity tiers.

### `check-review-report.py` — verify the structure baseline

A second driver, run on the review *report* (not the source files), after the
report is written:

```bash
python3 check-review-report.py <report.md> [--root <framework-project-root>]
```

It reads the report's mandatory `Structure baseline:` field and checks it against
disk. Exit `0` grounded (the field names a `.coding-standards-structure` that
exists), `1` declared skip (`NOT RECORDED` with a reason — surface it), `2`
inconsistent (the field claims a structure with no file behind it, or is missing).
This closes the one gap a `Write`/`Edit` hook structurally can't: resolving and
recording the project structure (SKILL.md Step 4) is a pre-review conversational
step, not a write event, so nothing fires when it's skipped. The report is the
artifact every review produces, and the file on disk is ground truth — a review
that skipped Step 4 leaves no structure file, and exit `2` catches it. See
`references/review-report.md`.

## Installation

### Step 1 — Install the skill files

```bash
# Project scope (default)
npx skills add willey-labs/agent-skills

# Or global scope, Claude Code only
npx skills add willey-labs/agent-skills -g -a claude-code
```

### Step 2 — Hooks auto-install on first skill activation

The skill's `SKILL.md` declares a Step 0 directive that runs
`bootstrap.py` the first time the skill activates in a session. That
script wires every hook in this directory into the correct
`settings.json` — `~/.claude/settings.json` for global installs,
`<project>/.claude/settings.json` for project installs — detected
deterministically from the SKILL.md's own path. **You do not need to
paste anything into settings.json by hand.**

After the first activation you'll see:

```
coding-standards: Wired 12 PreToolUse hooks into <path>/settings.json (<scope>).
```

(12 of the 13 can block on exit 2. `block-god-file.py` and `block-debug-artifacts.py` additionally exit 0 with an advisory — god-file on raw size / flat folders, debug-artifacts on print-style residue / commented-out code; `block-structure-file-violations.py` only fires on the `.coding-standards-structure` / `.coding-standards-ignore` config files, and additionally exits 0 with an advisory naming added ignore-file exemptions. `advise-comment-slop.py` never blocks — comment prose can't be hard-blocked at the precision bar, so it only ever advises.)

plus a `PostToolUse` recorder and a `Stop` comment judge (see above).

Restart the agent session once for Claude Code to pick up the hooks; from
the next session on, blocking is automatic on every Write/Edit/MultiEdit.

The bootstrap is **idempotent**: re-runs are noops unless the skill was
upgraded, in which case the previous hook entry is replaced. Unrelated
`PreToolUse` entries and other settings are preserved untouched.

### Manual bootstrap (e.g. you skipped the agent on first activation)

```bash
python3 ~/.claude/skills/coding-standards/bootstrap.py
# or, for a project install
python3 ./.claude/skills/coding-standards/bootstrap.py
```

Same script, same logic. Run from anywhere; the script resolves its own
location and decides scope from there.

### settings.example.json

`settings.example.json` in this directory is provided as a **reference**
for what the bootstrap writes. You shouldn't need to copy it manually
unless you're customizing the hook list or running on an agent that
doesn't auto-run `SKILL.md` Step 0.

> **Write-time blocking is Claude Code only.** These scripts implement the
> Claude Code PreToolUse contract (exit 2 + stderr); a violating Write/Edit is
> hard-stopped before it lands. That hard block runs only on agents implementing
> *that exact* contract — today, Claude Code. Other agents that support skills
> still install the skill and get the rules as **guidance the model applies**, but
> no write-time block: the model can drift and the violation is written anyway.
> Cline is the concrete example of why these don't port for free — its hooks expect
> a JSON `{"cancel": true}` on stdout, not exit 2, so they won't block under it
> as-is. For a deterministic check on any agent, run `review-files.py` as a manual
> linter (it reports; it never blocks).

## What the agent sees on a block

Each hook exits `2` and writes the violation list to stderr:

```
coding-standards hook blocked this write — fix the violations and try again.
See skills/coding-standards/references/common/ for cited rules (FN-005, NM-006).
  - /repo/src/foo.ts:1 — NM-006: Hungarian notation `strName`; drop the `str` prefix
```

The agent reads the message, fixes the violation, retries. No human
intervention needed for common cases.

## Exclusions — files this skill never touches

The skill enforces rules on **your code**, not on code owned by external tools. Every hook checks `_exclusions.py` first and exits 0 silently on excluded files. A file is excluded if any of:

**1. Its path matches a built-in default.** Highlights (full list in `_exclusions.py:DEFAULT_EXCLUSIONS`):

| Category | Patterns |
|---|---|
| Installed deps | `**/node_modules/**`, `**/vendor/**`, `**/bower_components/**` |
| shadcn/ui | `**/components/ui/**` (matches all monorepo variants: `packages/components/ui/**`, `apps/web/src/components/ui/**`, etc.) |
| ORM migrations | `**/prisma/migrations/**`, `**/drizzle/migrations/**`, `**/alembic/versions/**`, `**/migrations/[0-9][0-9][0-9][0-9]_*.py` (Django — all 4-digit prefixes, not just `0001_`) |
| Codegen | `**/generated/**`, `**/*.gen.ts`, `**/zz_generated.*`, `**/*_pb.go`, `**/*.designer.cs`, `**/*.g.cs`, `**/*.AssemblyInfo.cs` (.NET) |
| Build outputs | `**/dist/**`, `**/build/**`, `**/.next/**`, `**/.nuxt/**`, `**/.output/**` (Nuxt 3), `**/.svelte-kit/**`, `**/target/**`, `**/bin/**`, `**/obj/**` |
| Framework toolchain | `**/.expo/**` + `**/ios/Pods/**` (Expo/RN), `**/bootstrap/cache/**` + `**/_ide_helper*.php` (Laravel), `**/platforms/**` (NativeScript) |
| Tool caches / coverage | `**/.pytest_cache/**`, `**/.mypy_cache/**`, `**/.ruff_cache/**`, `**/.tox/**`, `**/*.egg-info/**`, `**/coverage/**`, `**/.turbo/**`, `**/.vercel/**`, `**/.vite/**` |
| Lock files | `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`, `**/composer.lock`, `**/Cargo.lock`, `**/go.sum`, `**/poetry.lock`, `**/uv.lock` |
| Skill artifacts | `**/.coding-standards/**` (the skill's own generated review reports) |

**2. Its content has a generation marker** in the first 10 lines (case-insensitive substring): `@generated`, `DO NOT EDIT`, `automatically generated`, `Code generated by`, `@autogenerated`, `@codegen`.

**3. It matches a pattern in `.coding-standards-ignore`** at the project root (gitignore-style). Bootstrap seeds a commented template of this file on first run so it's discoverable; you add patterns to it:

```
# .coding-standards-ignore
# Patterns are gitignore-style:
#   *      matches any chars except /
#   **     matches zero or more path segments
#   ?      matches one char except /
#   [..]   character class
#   #      comment
#   blank lines ignored

# Our shared design system is shadcn-generated end to end
packages/design-system/src/**

# Vendored from upstream — don't enforce our rules here
src/third-party/**

# This one file is intentionally weird, leave it alone
src/weirdo.ts
```

Custom patterns extend the defaults — they don't replace them. The project root is the first ancestor directory containing `.git`, `package.json`, `pyproject.toml`, `go.mod`, `composer.json`, `pom.xml`, or `.coding-standards-ignore` itself.

**Monorepo support is built in.** The `**/` prefix on default patterns matches any depth, so `**/components/ui/**` correctly excludes shadcn output regardless of whether your project uses `src/`, `apps/<app>/src/`, `packages/components/`, or any other monorepo layout. Note this exempts **any** folder named `components/ui`, not only shadcn-generated ones — if you hand-write code there, enforcement is off for it (move it or rename the folder if you want it checked).

## Required: TypeScript/JavaScript AST checks

Python AST checks are always on (uses stdlib `ast`). For TypeScript/JavaScript,
the AST-level checks (FN-001 function length, precise FN-005 arg count, OD-004
hybrid class detection) require `tree-sitter` — and they are **mandatory**:

```bash
pip install tree-sitter tree-sitter-typescript tree-sitter-javascript
```

`bootstrap.py` installs these for you (needs **Python 3.10+**; falls back to a
dedicated venv on a PEP 668 externally-managed host) and **refuses to wire the
hooks until the grammars load** — there is no silent regex-only downgrade at
the bootstrap level. The regex fallback in `block-ts-violations.py` remains
only as a defensive safety net for the case where the hook is invoked without
the grammars (e.g. a project-scope PATH `python3` that differs from the
interpreter tree-sitter was installed into).

Adds ~25 MB to the install footprint per language grammar.

## False-positive policy

Each rule was chosen because it has near-zero false-positive rate. Tradeoffs
deliberately made:

- **Single-char Hungarian prefixes** (`b, i, n, o, a` from the original draft)
  were **dropped** — they false-positive on legitimate names like `aUser`,
  `iValue`. The skill's NM-001 still catches those via the agent in review;
  hard-blocking at write time was too aggressive.
- **Java `Object` and Python `object`** are not blocked — too common in
  legitimate code. The agent catches those via the references during review.
- **Kotlin `Any` IS blocked** — the Kotlin ecosystem uses `Any` as a real
  escape hatch and the rule is cleaner there.
- **Go function arg count counts named parameters**, not type groups —
  `func F(a, b, c, d int)` is 4 params, blocked. This matches the rule's
  intent (mental-load count, not type-declaration count).

## What these hooks deliberately do NOT catch

Regex hits a precision ceiling fast. The skill's other rules — command/query
separation (FN-009), Law of Demeter (OD-003), error boundary translation
(EH-002), object-vs-data choice (OD-002), the comment-prose judgement behind
CM-001 to CM-004 (is this narration, does it say *what* instead of *why*, does the
docstring add anything — `advise-comment-slop.py` catches only the mechanical
tells), every rule in the framework-specific `structure.md` files — rely on the agent
reading the references and applying judgement. (FN-001 length and OD-004 hybrid classes ARE caught: precisely on
TS/JS/Python by the AST hooks, and FN-001 as a blunt advisory on Go/C#/Java/
Kotlin/PHP via `block-god-file.py`. OD-004 stays review-only on the non-AST
languages — a regex hybrid-class detector there has too high a false-positive
rate to ship even as an advisory.)

**The Bash bypass is not hard-enforced — by design.** Every hook matches
`Write|Edit|MultiEdit`, so a file written through the shell (`> file`, `tee`,
`sed -i`, a heredoc) evades all of them. A PreToolUse hook on `Bash` *could*
block shell writes to source files, but a precise low-false-positive version
isn't achievable (legitimate build/codegen scripts write source too) and it
would add a process spawn to every shell command. So the bypass is closed by
instruction instead: `SKILL.md` directs the agent to author only through
Write/Edit, and to run `review-files.py` over anything a tool generates outside
that path. A compliant agent never bypasses; this is a soft guard, not a gate.

For AST-level checks (function length, hybrid class detection, real return-
type analysis), an upgrade path is to replace the regex backends with
language parsers (`@typescript-eslint/parser`, `ast`, `go/parser`, Roslyn,
`php-parser`, JavaParser). Out of scope for stdlib-only hooks.

## Coverage map vs supported frameworks

| Framework | Language | Hook | Notes |
|---|---|---|---|
| Next.js | TS/JS | `block-ts-violations.py` | + path checks |
| NestJS | TS | `block-ts-violations.py` | + path checks |
| React Native / Expo | TS/JS | `block-ts-violations.py` | + path checks |
| NativeScript | TS/JS | `block-ts-violations.py` | + path checks |
| Cocos Creator | TS | `block-ts-violations.py` | + path checks |
| Vanilla JS/TS | TS/JS | `block-ts-violations.py` | + path checks |
| Node Express/Fastify | TS/JS | `block-ts-violations.py` | + path checks |
| Vue / Nuxt / Svelte | `.vue` / `.svelte` SFC | `block-ts-violations.py` | regex AND AST checks run on extracted `<script>` blocks (ISS-010) |
| Django | Python | `block-py-violations.py` | + path checks |
| FastAPI | Python | `block-py-violations.py` | + path checks |
| Flask | Python | `block-py-violations.py` | + path checks |
| Go HTTP | Go | `block-go-violations.py` | + path checks |
| Laravel | PHP | `block-php-violations.py` | + path checks |
| C# / .NET | C# | `block-csharp-violations.py` | + path checks |
| Spring Boot | Java / Kotlin | `block-jvm-violations.py` | + path checks |
