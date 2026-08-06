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
- `comments.md` — no narration, comments say *why* not *what*, no redundant docstrings/banners, no filler or change-narration (review-only)
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

The agent loads `common/` (all eight files) plus the matching framework `structure.md` on every code-writing or review task.

### `writing-standards`

The companion to `coding-standards`: that one governs code, this one governs **documents** — READMEs, specs, rules, skills, design docs, guides, reviews.

Two rule sets (`skills/writing-standards/references/common/`):
- `source-to-deliverable.md` (SD-*) — turn a *source* into a deliverable without echoing it: code→doc describes what the system does, with no code or code-identifiers; discussion→rule states the general principle, not the specific example just discussed.
- `anti-slop.md` (SL-*) — the patterns that read as machine-padded filler (hedging, hype words, throat-clearing, cheerleading, reflexive formatting, padding), each with a fix.

It does **not** block at write time — a document isn't a single Write the way a function is. Instead its bootstrap wires two hooks that inject a short reminder of the rules into the session: `SessionStart` at boot and `UserPromptSubmit` on every prompt, so the rules don't fade as the conversation grows. The full rules are read from `references/common/` when a document is actually written. The hook is stdlib-only — no dependency install, no venv. Wire it with `python3 skills/writing-standards/bootstrap.py` (or it auto-wires on first activation, like `coding-standards`); restart the session once.

## How the skill picks a framework

`SKILL.md` Step 3 has the authoritative detection table (per-framework signals plus the file types each framework owns) — see it for the exact rules rather than relying on examples here, which drift. The shape: each row pairs a framework with repo signals (config files, dependency keys, distinctive file types). Matching is **file-type-aware** — a row only wins if it owns the extension of the file being edited, so a `.php` file in a Laravel + Inertia/Vue repo resolves to `laravel` while a `.vue` in the same repo resolves to `vue-nuxt`. In monorepos the agent picks per file, not per repo. When signals are missing, it asks rather than guesses.

A framework the skill **recognizes but has no structure reference for** (Angular, Svelte/SvelteKit, Astro, Remix, …) is declined explicitly: the agent says so, applies the universal `common/` rules (still enforced by the language hooks on Claude Code, guidance elsewhere — see [enforcement per agent](#what-enforcement-means-per-agent)), and keeps the project's existing layout — it does **not** fall back to the vanilla-js business-folder/barrel layout, which would fight those frameworks' own conventions.

## Installation

### 1. Install the skill via the `skills` CLI

```bash
# Project scope (committed with your project, shared with team)
npx skills add willey-labs/agent-skills

# Global scope (available across all projects)
npx skills add willey-labs/agent-skills -g
```

The `skills` CLI auto-detects which agents you have installed (Claude Code, Cursor,
Codex, OpenCode, and 50+ more); pass `-a claude-code` to target one explicitly.
Installation reaches all of them; write-time **blocking** does not — that part is
Claude Code only (see [the enforcement note](#what-enforcement-means-per-agent)
below). On every other agent the rules ride along as guidance, not a hard block.

Preview before installing: `npx skills add willey-labs/agent-skills --list`.

### 2. Hooks auto-wire on first use — no extra step

The first time the `coding-standards` skill activates in a session (e.g.
you ask Claude Code to "write a component" or "review this PR"), Step 0
of the skill runs `bootstrap.py`. That script:

1. Detects the install scope from its own path (`~/.claude/skills/` → global,
   `<project>/.claude/skills/` → project) and targets the correct
   `settings.json`.
2. Adds a single PreToolUse entry registering all 11 enforcement hooks
   (1 path-checker, 6 language content-checkers, 1 cross-language swallowed-error
   checker, 1 cross-language debug-artifact checker, 1 ST-008 god-file checker that
   blocks on declaration count and advises on size, 1 checker that keeps
   `.coding-standards-structure` to placement only). Existing unrelated `PreToolUse`
   entries and other settings are preserved byte-for-byte.
3. Is idempotent: re-running is a noop unless the skill was upgraded, in
   which case the entry is replaced with the new hook list.

After the first run you'll see something like:

```
coding-standards: Wired 12 PreToolUse hooks into /path/.claude/settings.json (project).
```

**Restart the agent session once** for Claude Code to pick up the new
hooks. From the next session on, the language-aware enforcement (`any`,
Hungarian, 4+ argument functions, junk-drawer paths, deep imports, etc.)
runs on every Write/Edit/MultiEdit automatically.

See `skills/coding-standards/hooks/README.md` for what each hook catches
per language.

Two of the wired hooks work on comments rather than code. Comment prose is the one
rule family a pattern can't settle — a constraint the next reader needs and an author
defending an edit are made of the same words — and the pass that wrote a comment is
the worst judge of whether it earns its place. So when a turn tries to end, the
comments it added go to a **separate model call** with the comment rules, and a
delete-or-shorten verdict holds the turn open until it's applied. Deleting or trimming
a comment can't change behaviour, so it's applied without asking; a verdict that's
genuinely wrong may be kept with the reason stated in the reply.

That costs one short model call per turn that wrote source files, and none when those
files gained no comments. It defaults to `sonnet`; set `CODING_STANDARDS_JUDGE_MODEL`
to pick another. A session is held open at most twice, and every failure — no CLI, a
timeout, an unparseable answer — lets the turn end.

#### What enforcement means per agent

> **Distribution is not enforcement.** The skill *installs* on 50+ agents; the
> hard, can't-ignore **write-time block** runs on far fewer. Two tiers:
>
> - **Hard block (Claude Code).** The hooks implement Claude Code's PreToolUse
>   exit-2 + stderr contract. A Write/Edit that violates a rule is stopped before it
>   lands and the agent must fix it. Any agent
>   that implements *that exact* contract would block the same way; today that's
>   Claude Code.
> - **Guidance everywhere else (Cursor, Codex, OpenCode, Cline, …).** The skill
>   still installs and the rules still ride along — the model reads them and is
>   expected to follow them — but **nothing blocks a violation at write time.** If
>   the model drifts, the code is written anyway. Cline is a concrete example of why
>   the scripts don't port for free: its hooks expect a JSON `{"cancel": true}` on
>   stdout, not exit 2, so these scripts won't block under it as-is.
>
> So: the *standards* reach every agent; the *hard block* reaches Claude Code. If
> you need the block on another agent, you'd have to implement that agent's own hook
> contract — it isn't shipped here. For a code review pass on any agent, run
> `hooks/review-files.py` as a manual linter (it reports; it doesn't block).

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
is idempotent, and a `SessionStart` hook runs it for you: at every session start it
checks whether every hook the version ships is actually wired, and re-runs the
installer itself when any is missing. So an update picks up new hooks **and**
re-applies the permission allow-rules (reading the skill's references and running its
scripts without a prompt) without anyone being asked to act. That rewrites your
`settings.json` — deliberately, because a session that silently checks nothing is the
worse outcome. Because settings are read at session start, the repair lands on the
*next* session; the check says so when it runs. To apply immediately instead of
waiting, run `python3 <skill-dir>/bootstrap.py` and restart.

### Turning it off

Enforcement is always-on once wired — there is no rule toggle (toggles are blocked by design). To disable it, remove the skill's `PreToolUse` entry from the relevant `settings.json` (project or `~/.claude`), or uninstall the skill; for a single path or legacy file, add it to `.coding-standards-ignore` with a `# reason:`. The comment judge is the one part with a running cost, so it comes off separately: drop the `Stop` entry to stop the model call, and the `PostToolUse` entry with it. Details in `skills/coding-standards/references/bootstrap.md`.

## Status

The structure rules have been self-reviewed against representative project
layouts. Eleven PreToolUse hooks (one universal path-checker, six language
content-checkers, one cross-language swallowed-error checker, one cross-language
debug-artifact checker, one ST-008 god-file checker that blocks on declaration
count and advises on size, and one checker that keeps `.coding-standards-structure`
to placement only) in `skills/coding-standards/hooks/` enforce what they can detect
reliably. That write-time blocking is **Claude Code only** (the exit-2 PreToolUse
contract); on every other agent the same checks ship as guidance, not a hard block —
see [What enforcement means per agent](#what-enforcement-means-per-agent).
The regex checks hard-block `any`/`Any`/`interface{}`/`dynamic`/`mixed` (OD-006),
Hungarian notation, 4+/5+ argument functions (the line follows the language —
positional vs named-argument — with framework carve-outs for DI constructors,
records, and parameter bindings), swallowed errors (empty `catch`, `except: pass`,
discarded `err` — EH-002), debug residue (`debugger`, `breakpoint()`, `dd()` —
FMT-005, with `console.log`/`print` advised), junk-drawer paths and folders,
dot/star imports, deep imports, and parent traversal. On TypeScript/JavaScript (via tree-sitter) and Python (via the stdlib
`ast`), an AST layer additionally hard-blocks the structural rules a real parse is
needed for: FN-001 (function body length), FN-005 (precise argument count), and
OD-004 (hybrid classes). The advisory hook warns — never blocks — on god-file size
and flat-folder growth. Review treats every finding as a violation to fix — there
are no severity tiers. Everything else relies on the agent reading the references
and applying judgement during write/review. For mechanical checks beyond these (dead code, complexity
metrics, etc.), pair with your project's linter (ESLint, PHPStan, Roslyn
analyzers, etc.).

## License

MIT
