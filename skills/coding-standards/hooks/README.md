# coding-standards hooks

PreToolUse hooks that hard-block Write/Edit/MultiEdit when high-precision
violations are detected. The agent sees the block as a tool error and must
fix the violation before retrying — that's the enforcement.

## Hooks shipped

| Hook | Scope | What it catches |
|---|---|---|
| `block-junk-paths.py` | All languages (path-only) | ST-005 junk-drawer filenames (`utils.ts`, `helpers.py`, `common.go`, ...); ST-005 corollary top-level mega-files (`src/types.ts`, `src/constants.ts`, ...) |
| `block-ts-violations.py` | `.ts .tsx .mts .cts .js .jsx .mjs .cjs .vue .svelte` | `any` (6 forms); NM-006 Hungarian; ST-003 deep imports; parent traversal. **AST checks (required — bootstrap installs tree-sitter):** FN-001 function length, FN-005 precise arg count, OD-004 hybrid class detection (OD-005 framework-boundary carve-out). Regex-only is a defensive fallback if the grammars are ever absent. |
| `block-py-violations.py` | `.py .pyi` | `typing.Any` (8 forms); NM-006 Hungarian snake_case; `from x import *`. **AST checks (always on — stdlib `ast`):** FN-001 function length, FN-005 precise arg count, OD-004 hybrid class detection with OD-005 framework-boundary carve-out (Model, BaseModel, Serializer, Form, etc.). |
| `block-go-violations.py` | `.go` | `interface{}` / `any` (param/return/var/map/slice); FN-005 4+ params (grouped or typed); `import . "fmt"` dot imports |
| `block-csharp-violations.py` | `.cs` | `dynamic` (var/list/dict); NM-006 Hungarian (`strName`, `m_field`, ...); FN-005 4+ params |
| `block-php-violations.py` | `.php` | `mixed` type; NM-006 Hungarian (`$strName`, ...); FN-005 4+ params |
| `block-jvm-violations.py` | `.java .kt .kts` | Star imports (`import com.foo.*`); FN-005 4+ params; Kotlin `Any` (annotation/generic) |
| `warn-god-file.py` | All source languages (advisory — exit 0) | ST-008 advisories, both directions. (1) God-file size: warns when a non-test/non-schema source file exceeds the project threshold (default 400 lines / 10 top-level declarations). (2) Flat-folder promotion: warns when a NEW source file lands in a folder already past the flat-sibling threshold (default 12 source units; front doors and test/schema/fixture siblings don't count) — 3+ themed siblings have earned a sub-feature folder (Rule of Three). Never blocks. Reads `god-file`, `god-file-max-lines`, `god-file-max-decls`, `flat-folder`, `flat-folder-max-files` keys from `.coding-standards-structure`. Skips test, schema, fixture, story, and excluded/generated files. |

### What runs on every Write/Edit/MultiEdit

All hooks run on each call. Each one checks the file extension first and
exits 0 cleanly if the file doesn't match its language. There's no
performance hit from registering them all.

`block-junk-paths.py` only fires on `Write` (path-based — Edit/MultiEdit
operate on already-accepted paths).

## Review mode — run the hooks as a linter (read-only)

The hooks above are **write-time**: they fire on `Write`/`Edit`/`MultiEdit`. A
code *review* writes nothing, so they don't fire on their own. To get the same
deterministic checks while reviewing existing files, run the bundled driver:

```bash
python3 review-files.py <file> [<file> ...]
git diff --name-only | python3 review-files.py --stdin
python3 review-files.py --json <file> ...     # machine-readable, for the orchestrator
```

It feeds each file's current content to every `block-*.py` hook as a synthetic
`Write` payload — identical to the write-time contract — and prints the
violations grouped by file. Excluded files are skipped exactly as at write time.
It always exits `0` (it reports; it never blocks). The skill's Review mode runs
this as its final deterministic pass — after the judgement pass / specialist
workers — and merges the findings in as must-fix.

## Installation

### Step 1 — Install the skill files

```bash
# Project scope (default)
npx skills add willey-labs/agent-skills

# Or global scope, Claude Code only
npx skills add willey-labs/agent-skills -g -a claude-code
```

CLI reference: [`vercel-labs/skills`](https://github.com/vercel-labs/skills).

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
coding-standards: Wired 8 PreToolUse hooks into <path>/settings.json (<scope>).
```

(7 blocking hooks + 1 advisory `warn-god-file.py` that exits 0 with a warning instead of blocking.)

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

> Write-time blocking via these hooks is a **Claude Code** feature (the exit-2
> + stderr PreToolUse contract these scripts implement). Cline also has hooks,
> but blocks via a different contract (a JSON `{"cancel": true}` response on
> stdout, not exit 2), so these scripts won't block under Cline as-is. Other
> agents that support skills still get the rule documentation, but not the
> write-time blocking.

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

Regex hits a precision ceiling fast. The skill's other rules — function
length (FN-001), command/query separation (FN-009), hybrid classes (OD-004),
Law of Demeter (OD-003), error boundary translation (EH-002), every rule
in the framework-specific `structure.md` files — rely on the agent reading
the references and applying judgement.

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
| Vue / Nuxt | `.vue` SFC | `block-ts-violations.py` | TS rules apply to `<script>` |
| Django | Python | `block-py-violations.py` | + path checks |
| FastAPI | Python | `block-py-violations.py` | + path checks |
| Flask | Python | `block-py-violations.py` | + path checks |
| Go HTTP | Go | `block-go-violations.py` | + path checks |
| Laravel | PHP | `block-php-violations.py` | + path checks |
| C# / .NET | C# | `block-csharp-violations.py` | + path checks |
| Spring Boot | Java / Kotlin | `block-jvm-violations.py` | + path checks |
