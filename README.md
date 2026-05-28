# agent-skills

Skills for [Claude Code](https://claude.com/claude-code) and other Anthropic-API-based agents.

## Skills in this repo

### `coding-standards`

Language-agnostic clean-code rules **plus** per-framework structure rules.

**Universal rules** (`skills/coding-standards/references/common/`):
- `functions.md` — size, argument count, side effects, command/query separation, exceptions over error codes
- `naming.md` — intention-revealing, no Hungarian, meaningful distinctions, pronounceable, searchable, no mental mapping
- `objects-and-data.md` — expose behavior not data, objects vs data structures, Law of Demeter, no hybrid classes
- `formatting.md` — newspaper rule, vertical spacing, declarations close to use
- `error-handling.md` — separate algorithm from error handling, translate at boundaries, define contracts first
- `code-principles.md` — SOLID, KISS, DRY

**Per-framework structure rules** (`skills/coding-standards/references/<framework>/structure.md`):
- `nextjs/` — Screaming Architecture + mandatory nesting (App Router)
- `nestjs/` — Package by feature, module per feature
- `laravel/` — Stock Laravel skeleton with capability subfolders inside each layer
- `vanilla-js/` — Folder-as-module + co-location (libraries, CLIs, frameworkless apps)
- `nativescript/` — Flat business folders with MVVM trio per page
- `react-native/` — Flat business folders with ESLint-enforced boundaries
- `csharp/` — Single project, flat business folders (vertical-slice flavoured)
- `node-express/` — Package by feature for plain Node backends
- `cocos-creator/` — Asset Bundles per feature (2.x and 3.x, TypeScript)

The agent loads `common/` (all six files) plus the matching framework `structure.md` on every code-writing or review task.

## How the skill picks a framework

`SKILL.md` has a detection table — `next.config.*` + `next` in `package.json` → `nextjs`, `composer.json` with `laravel/framework` → `laravel`, etc. When project signals are missing, the agent asks rather than guesses.

## Installation

Clone into a location your agent reads skills from:

```bash
git clone https://github.com/willey-labs/agent-skills.git ~/projects/willey-labs/agent-skills
```

For Claude Code, symlink (or copy) the individual skill folder into the skills path you use:

```bash
ln -s ~/projects/willey-labs/agent-skills/skills/coding-standards ~/.claude/skills/coding-standards
```

Or reference the skill path via your `~/.claude/settings.json` or per-project `.claude/settings.json`.

## Status

This is a working draft. The structure rules have been audited against real projects; the rules are reasonable but **not yet hard-enforced** — they rely on the agent applying them during write/review. Integration with project-level linters (ESLint, PHPStan, Roslyn analyzers, etc.) is the recommended way to catch mechanical violations; this skill covers the structural and intent-level rules that static tools can't see.

## License

MIT
