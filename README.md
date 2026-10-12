# agent-skills

Agent Skills for Claude Code, Cursor, Codex, OpenCode and other agents supported by the `skills` CLI.

## Skills

**`coding-standards`** — clean-code rules for writing and reviewing code: functions, naming, objects and data, formatting, comments, error handling, SOLID/KISS/DRY, and folder structure. On Claude Code it blocks violating writes before they land.

Framework structure rules:

- Frontend / mobile: Next.js, Vue/Nuxt, React Native/Expo, NativeScript, Cocos Creator
- Backend: NestJS, Node (Express/Fastify), Laravel, C#/.NET, Spring Boot, Django, FastAPI, Flask, Go HTTP
- Frameworkless: vanilla JS/TS libraries, CLIs and apps

The agent picks the framework per file from repo signals and asks when they are missing. A recognized framework without a structure reference (Angular, SvelteKit, Astro, Remix, …) gets the universal rules and keeps its existing layout.

**`writing-standards`** — rules for documents (READMEs, specs, design docs, reviews): describe what a system does without pasting its code, and cut filler, hedging and hype. It reminds the agent of the rules at session start and on every prompt; it never blocks a write.

## Install

```bash
npx skills add willey-labs/agent-skills        # project scope
npx skills add willey-labs/agent-skills -g     # global scope
npx skills add willey-labs/agent-skills --list # preview
```

Pass `-a claude-code` to target one agent.

Manual install:

```bash
git clone https://github.com/willey-labs/agent-skills.git ~/projects/willey-labs/agent-skills
ln -s ~/projects/willey-labs/agent-skills/skills/coding-standards ~/.claude/skills/coding-standards
python3 ~/.claude/skills/coding-standards/bootstrap.py
```

The first time `coding-standards` activates, the agent lists what the install changes and asks before running it:

- adds the skill's hooks and a `/coding-standards` command to the `settings.json` for its install scope, keeping your existing settings
- installs the tree-sitter Python packages (Python 3.10+; a dedicated venv on global installs and PEP 668 systems)
- adds allow-rules so the skill reads its own files and runs its own scripts without prompts
- seeds a commented `.coding-standards-ignore` at the project root

Restart the agent session once afterwards. `writing-standards` wires its reminder hook the same way and installs nothing.

## Enforcement

Claude Code blocks a violating Write/Edit before it lands, and the agent must fix it. Other agents receive the same rules as guidance only; nothing stops a violation. On any agent, `python3 <skill-dir>/hooks/review-files.py <files>` reports violations without blocking.

Blocked at write time on TypeScript/JavaScript, Python, Go, C#, PHP, Java and Kotlin:

- `any` (TypeScript), `Any` (Python, Kotlin), `dynamic` (C#), `mixed` (PHP)
- Hungarian notation
- functions with too many positional arguments
- over-long functions and hybrid classes (TS/JS and Python)
- swallowed errors and debugger calls
- junk-drawer files and folders (`utils`, `helpers`, `common`, `misc`)
- deep imports, star imports, parent-path traversal
- files with more than 10 top-level functions or classes
- added comments longer than one line (`CODING_STANDARDS_MAX_COMMENT_LINES` sets the limit); file headers and doc comments on a declaration (JSDoc, Javadoc, `///`, Go doc comments, Python docstrings) may run longer

Large files, print statements outside a program's entry point, commented-out code, filler comments and Go's `any`/`interface{}` get a warning instead of a block.

The comment judge is optional. When enabled (`bootstrap.py --with-comment-judge`, or a yes at install), a separate model call checks the comments each turn adds, and the agent must delete or shorten the ones it rejects. It costs one short call per such turn, defaults to `sonnet` (`CODING_STANDARDS_JUDGE_MODEL` changes it), and a failed call never blocks the turn. `--without-comment-judge` removes it.

Context cost: before writing or reviewing code, the agent reads about 125 KB of rules once per session (SKILL.md, the eight common rule files and one framework file).

## Update

```bash
npx skills add willey-labs/agent-skills          # CLI install
git -C ~/projects/willey-labs/agent-skills pull  # manual install
```

At each session start, the skill re-wires any hook the new version adds; the change applies from the next session. Run `python3 <skill-dir>/bootstrap.py` and restart to apply it now.

## Turn off

There is no per-rule toggle. To exempt a path, add it to `.coding-standards-ignore` with a `# reason:` comment. To turn the skill off for a scope, remove every hook entry it added to that scope's `settings.json`, or uninstall it. Details: `skills/coding-standards/references/bootstrap.md`.

## Development

`skills/coding-standards/hooks/tests/run-all.py` runs the hook regression suite; CI runs it on Linux and macOS and fails if the skill's own code draws any finding from its linter. `evals/` measures agent output with and without the skill. Contributor rules: [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE)
