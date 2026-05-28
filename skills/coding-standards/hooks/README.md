# coding-standards hooks

PreToolUse hooks that hard-block Write/Edit/MultiEdit when high-precision
violations are detected. The agent sees the block as a tool error and must
fix the violation before retrying — that's the enforcement.

## Hooks shipped

| Hook | Scope | What it catches |
|---|---|---|
| `block-junk-paths.py` | All languages (path-only) | ST-005 junk-drawer filenames (`utils.ts`, `helpers.py`, `common.go`, ...); ST-005 corollary top-level mega-files (`src/types.ts`, `src/constants.ts`, ...) |
| `block-ts-violations.py` | `.ts .tsx .mts .cts .js .jsx .mjs .cjs .vue .svelte` | `any` (6 forms); NM-006 Hungarian (`strName`, `arrItems`, ...); FN-005 4+ positional args; ST-003 deep imports; parent traversal `../../../` |
| `block-py-violations.py` | `.py .pyi` | `typing.Any` (8 forms); NM-006 Hungarian snake_case (`str_name`, ...); FN-005 4+ args (ignores `self`/`cls`); `from x import *` |
| `block-go-violations.py` | `.go` | `interface{}` / `any` (param/return/var/map/slice); FN-005 4+ params (grouped or typed); `import . "fmt"` dot imports |
| `block-csharp-violations.py` | `.cs` | `dynamic` (var/list/dict); NM-006 Hungarian (`strName`, `m_field`, ...); FN-005 4+ params |
| `block-php-violations.py` | `.php` | `mixed` type; NM-006 Hungarian (`$strName`, ...); FN-005 4+ params |
| `block-jvm-violations.py` | `.java .kt .kts` | Star imports (`import com.foo.*`); FN-005 4+ params; Kotlin `Any` (annotation/generic) |

### What runs on every Write/Edit/MultiEdit

All hooks run on each call. Each one checks the file extension first and
exits 0 cleanly if the file doesn't match its language. There's no
performance hit from registering them all.

`block-junk-paths.py` only fires on `Write` (path-based — Edit/MultiEdit
operate on already-accepted paths).

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
coding-standards: Wired 7 PreToolUse hooks into <path>/settings.json (<scope>).
```

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

> Hooks are a Claude Code / Cline feature. Other agents that support skills
> still get the rule documentation, but not the write-time blocking.

## What the agent sees on a block

Each hook exits `2` and writes the violation list to stderr:

```
coding-standards hook blocked this write — fix the violations and try again.
See skills/coding-standards/references/common/ for cited rules (FN-005, NM-006).
  - /repo/src/foo.ts:1 — NM-006: Hungarian notation `strName`; drop the `str` prefix
```

The agent reads the message, fixes the violation, retries. No human
intervention needed for common cases.

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
