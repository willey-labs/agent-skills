# Bootstrap — full detail

`bootstrap.py` wires the PreToolUse enforcement hooks and the `/coding-standards` slash command into the correct `settings.json`. SKILL.md Step 0 has the lean invocation; this file is the full contract — read it only when bootstrap misbehaves or you need a flag.

> Paths here (`bootstrap.py`, `hooks/…`) are relative to the **skill root** — the directory holding `SKILL.md`, one level up from this `references/` folder.

## What it does, in order

1. **Readiness check** — Python version (the stdlib hooks need 3.9+; the optional tree-sitter TS/JS AST checks need **3.10+** — current `tree-sitter` / `tree-sitter-javascript` wheels dropped 3.9), Python command (`python` vs `python3`), pip availability, virtualenv detection, platform (Windows / macOS / Linux), tree-sitter package availability.
2. **Auto-install missing tree-sitter packages** — when invoked with `--auto-install` (recommended for agent contexts; the bootstrap can't prompt from a non-TTY).
3. **Wire PreToolUse hooks** into the correct `settings.json` (project vs global, auto-detected from the SKILL.md install path).
4. **Symlink `/coding-standards` slash command** into `.claude/commands/`.
5. **Seed a `.coding-standards-ignore` template** at the project root (project scope: the `.claude` parent; global scope: the cwd's project root). Commented examples only, never overwrites an existing file — its purpose is discoverability, so users know the opt-out exists. Patterns added there extend the built-in `DEFAULT_EXCLUSIONS`, they don't replace them.

The bootstrap detects the right Python command at runtime and writes it into `settings.json`, so the hook commands work cross-platform.

## Invocation

**Agent / non-TTY context** (recommended):

```bash
python3 <skill-dir>/bootstrap.py --auto-install
```

or, if `python3` isn't on PATH (some Windows installs):

```bash
python <skill-dir>/bootstrap.py --auto-install
```

**Interactive (user shell)** — prompts for tree-sitter install confirmation when stdin is a TTY:

```bash
python3 <skill-dir>/bootstrap.py
```

## Flags

| Flag | Purpose |
|---|---|
| `--check` | Only report readiness; do not install or wire anything. |
| `--auto-install` | Install missing tree-sitter without prompting. Use from agent context. |
| `--skip-install` | Skip the tree-sitter install offer entirely. |

## Idempotency

- First run: prints readiness, installs missing deps, wires hooks, links command, prints `Wired …`.
- Re-run with no changes: prints `already installed … No changes`.
- Re-run after skill upgrade: replaces the previous hook entry; unrelated `PreToolUse` entries are preserved.

## What to tell the user after it runs

- Reports `Wired` or `Updated` → tell the user to **restart the agent session** so the hooks activate.
- Reports `Install OK` for tree-sitter → also restart, so the TS/JS AST checks load.
- Exits with `Blocking issues:` (Python too old, etc.) → surface the issue verbatim and ask the user to resolve it before proceeding.
- Exits with `cannot determine install scope` → the skill is invoked from outside a `.claude/skills/` tree. Point at `README.md`'s install command and skip Step 0; the rest of the skill still applies (rules enforced softly, no write-time blocking).
