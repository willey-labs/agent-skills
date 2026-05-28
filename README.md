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
2. Adds a single PreToolUse entry registering all 7 enforcement hooks.
   Existing unrelated `PreToolUse` entries and other settings are
   preserved byte-for-byte.
3. Is idempotent: re-running is a noop unless the skill was upgraded, in
   which case the entry is replaced with the new hook list.

After the first run you'll see something like:

```
coding-standards: Wired 7 PreToolUse hooks into /path/.claude/settings.json (project).
```

**Restart the agent session once** for Claude Code to pick up the new
hooks. From the next session on, the language-aware enforcement (`any`,
Hungarian, 4+ argument functions, junk-drawer paths, deep imports, etc.)
runs on every Write/Edit/MultiEdit automatically.

See `skills/coding-standards/hooks/README.md` for what each hook catches
per language.

> Hooks are a Claude Code (and Cline) feature. On other agents the rule
> documentation still applies, but write-time blocking won't.

### Manual install (no CLI)

```bash
git clone https://github.com/willey-labs/agent-skills.git ~/projects/willey-labs/agent-skills
ln -s ~/projects/willey-labs/agent-skills/skills/coding-standards ~/.claude/skills/coding-standards
python3 ~/.claude/skills/coding-standards/bootstrap.py
```

The bootstrap script handles the hook wiring; restart the agent after
the first successful run.

## Status

The structure rules have been audited against real projects. Seven
language-specific PreToolUse hooks in `skills/coding-standards/hooks/`
hard-block the high-precision violations regex can catch reliably
(`any`/`Any`/`interface{}`/`dynamic`/`mixed`, Hungarian notation, 4+ argument
functions, junk-drawer paths, dot/star imports, deep imports, parent
traversal). Everything else relies on the agent reading the references and
applying judgement during write/review. For mechanical checks beyond regex
(function length, hybrid class detection), pair with your project's linter
(ESLint, PHPStan, Roslyn analyzers, etc.).

## License

MIT
