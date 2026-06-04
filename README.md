# agent-skills

Skills for [Claude Code](https://claude.com/claude-code) and other Anthropic-API-based agents.

## Skills in this repo

### `coding-standards`

Language-agnostic clean-code rules **plus** per-framework structure rules.

**Universal rules** (`skills/coding-standards/references/common/`):
- `functions.md` — size, argument count, side effects, command/query separation, idiomatic failure handling per language
- `naming.md` — intention-revealing, no Hungarian, meaningful distinctions, pronounceable, searchable, no mental mapping, one word per concept, solution-vs-problem domain names
- `objects-and-data.md` — expose behavior not data, objects vs data structures, sum-type escape hatch, Law of Demeter, no hybrid classes (with framework-boundary carve-out)
- `formatting.md` — newspaper rule, vertical spacing, declarations close to use, line-length convention
- `error-handling.md` — separate algorithm from error handling, translate at boundaries (exceptions & Result/Either), async failure rules
- `code-principles.md` — SOLID, KISS, DRY
- `structure.md` — universal structural rules: folder-as-module, no deep imports, Rule of Three, no junk-drawer files, generic names at the design system

**Per-framework structure rules** (`skills/coding-standards/references/<framework>/structure.md`):

*Frontend / mobile*
- `nextjs/` — Screaming Architecture + mandatory nesting (App Router)
- `vue-nuxt/` — Flat business folders for Vue 3 / Nuxt 3 (Composition API, Pinia, composables)
- `react-native/` — Flat business folders with ESLint-enforced boundaries (Expo + bare RN)
- `nativescript/` — Flat business folders with MVVM trio per page
- `cocos-creator/` — Asset Bundles per feature (2.x and 3.x, TypeScript)

*Backend*
- `nestjs/` — Package by feature, module per feature
- `node-express/` — Package by feature for plain Node backends
- `laravel/` — Stock Laravel skeleton with capability subfolders inside each layer
- `csharp/` — Single project, flat business folders (vertical-slice flavoured)
- `spring-boot/` — Package by feature with Spring DI and Jakarta validation (Java/Kotlin)
- `django/` — Django apps as capabilities, with an added services layer
- `fastapi/` — Package by feature with APIRouter, Pydantic schemas, async-first
- `flask/` — Application factory + Blueprints per feature
- `go-http/` — `cmd/` + `internal/<feature>` with errors-as-values and consumer-defined interfaces

*Frameworkless*
- `vanilla-js/` — Folder-as-module + co-location (libraries, CLIs, frameworkless apps)

The agent loads `common/` (all seven files) plus the matching framework `structure.md` on every code-writing or review task.

## How the skill picks a framework

`SKILL.md` has a detection table — `next.config.*` + `next` in `package.json` → `nextjs`, `composer.json` with `laravel/framework` → `laravel`, `manage.py` + `settings.py` → `django`, `pom.xml` with `spring-boot-starter-*` → `spring-boot`, `go.mod` + `gin-gonic/gin` → `go-http`, etc. In monorepos with multiple frameworks coexisting (web + API + mobile), the agent picks the framework by the file being edited rather than by the repo as a whole. When project signals are missing, the agent asks rather than guesses.

## Installation

### 1. Install the skill via the `skills` CLI

```bash
# Project scope (committed with your project, shared with team)
npx skills add willey-labs/agent-skills

# Global scope (available across all projects)
npx skills add willey-labs/agent-skills -g
```

Uses the [skills.sh](https://skills.sh) / [agentskills.io](https://agentskills.io)
CLI from [`vercel-labs/skills`](https://github.com/vercel-labs/skills).
The CLI auto-detects which agents you have installed (Claude Code, Cursor,
Codex, OpenCode, and 50+ more); pass `-a claude-code` to target one explicitly.

Preview before installing: `npx skills add willey-labs/agent-skills --list`.

### 2. Hooks auto-wire on first use — no extra step

The first time the `coding-standards` skill activates in a session (e.g.
you ask Claude Code to "write a component" or "review this PR"), Step 0
of the skill runs `bootstrap.py`. That script:

1. Detects the install scope from its own path (`~/.claude/skills/` → global,
   `<project>/.claude/skills/` → project) and targets the correct
   `settings.json`.
2. Adds a single PreToolUse entry registering all 9 enforcement hooks
   (1 path-checker, 6 language content-checkers, 1 ST-008 god-file checker
   that blocks on declaration count and advises on size, 1 checker that keeps
   `.coding-standards-structure` to placement only). Existing unrelated
   `PreToolUse` entries and other settings are preserved byte-for-byte.
3. Is idempotent: re-running is a noop unless the skill was upgraded, in
   which case the entry is replaced with the new hook list.

After the first run you'll see something like:

```
coding-standards: Wired 9 PreToolUse hooks into /path/.claude/settings.json (project).
```

**Restart the agent session once** for Claude Code to pick up the new
hooks. From the next session on, the language-aware enforcement (`any`,
Hungarian, 4+ argument functions, junk-drawer paths, deep imports, etc.)
runs on every Write/Edit/MultiEdit automatically.

See `skills/coding-standards/hooks/README.md` for what each hook catches
per language.

> Write-time blocking via these hooks is a **Claude Code** feature (the
> exit-2 + stderr PreToolUse contract). Cline also has hooks, but uses a
> different contract (a JSON `{"cancel": true}` response on stdout, not exit
> 2), so these scripts won't block under Cline as-is. On other agents the
> rule documentation still applies, but write-time blocking won't.

### Manual install (no CLI)

```bash
git clone https://github.com/willey-labs/agent-skills.git ~/projects/willey-labs/agent-skills
ln -s ~/projects/willey-labs/agent-skills/skills/coding-standards ~/.claude/skills/coding-standards
python3 ~/.claude/skills/coding-standards/bootstrap.py
```

The bootstrap script handles the hook wiring; restart the agent after
the first successful run.

### Updating

To move to a newer version, update the files the normal way:

```bash
# CLI install — re-run to pull the latest
npx skills add willey-labs/agent-skills

# Manual / git install
git -C ~/projects/willey-labs/agent-skills pull
```

You **don't** need to re-run anything by hand, or tell your team to. `bootstrap.py`
is idempotent, and the skill re-runs it on activation (`SKILL.md` Step 0 — "after a
skill update"), so the next session picks up any new hooks **and** re-applies the
permission allow-rules (reading the skill's references and running its scripts
without a prompt). Because settings are read at session start, the *first* session
after an update may still prompt once; the next session is clean. To apply
immediately instead of waiting, run `python3 <skill-dir>/bootstrap.py` and restart.

## Status

The structure rules have been self-reviewed against representative project
layouts. Nine PreToolUse hooks (one universal path-checker, six language
content-checkers, one ST-008 god-file checker that blocks on declaration count
and advises on size, and one checker that keeps `.coding-standards-structure`
to placement only) in `skills/coding-standards/hooks/` enforce what they can
detect reliably.
The regex checks hard-block `any`/`Any`/`interface{}`/`dynamic`/`mixed`,
Hungarian notation, 4+ argument functions, junk-drawer paths, dot/star imports,
deep imports, and parent traversal. On TypeScript/JavaScript (via tree-sitter)
and Python (via the stdlib `ast`), an AST layer additionally hard-blocks the
structural rules a real parse is needed for: FN-001 (function body length),
FN-005 (precise argument count), and OD-004 (hybrid classes). The advisory hook
warns — never blocks — on god-file size and flat-folder growth. Everything else
relies on the agent reading the references and applying judgement during
write/review. For mechanical checks beyond these (dead code, complexity
metrics, etc.), pair with your project's linter (ESLint, PHPStan, Roslyn
analyzers, etc.).

## License

MIT
