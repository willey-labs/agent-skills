# Bootstrap — full detail

`bootstrap.py` wires the PreToolUse enforcement hooks and the `/coding-standards` slash command into the correct `settings.json`. SKILL.md Step 0 has the lean invocation; this file is the full contract — read it only when bootstrap misbehaves or you need a flag.

> Paths here (`bootstrap.py`, `hooks/…`) are relative to the **skill root** — the directory holding `SKILL.md`, one level up from this `references/` folder.

## What it does, in order

1. **Readiness check** — Python version (**3.10+**, the floor of `REQUIRED_PACKAGES`; current `tree-sitter` / `tree-sitter-javascript` wheels dropped the 3.9 wheel), Python command (`python` vs `python3`), pip availability, virtualenv detection, platform (Windows / macOS / Linux), and whether every package in `REQUIRED_PACKAGES` imports.
2. **Install the missing required packages** — these are mandatory. In a non-TTY (agent) context the install always proceeds; on a TTY it confirms first. `--auto-install` skips the confirm. The strategy is **scope-aware**: a **global** install builds (or reuses) a dedicated `coding-standards` venv beside the hooks so they don't depend on whatever `python3` is first on PATH; a **project** install installs into the active interpreter and wires the portable `python3` name so the committed `settings.json` works across teammates (a managed venv is its PEP 668 fallback). If the packages still can't be loaded afterward, bootstrap reports a blocking issue and exits non-zero **without wiring the hooks** — there is no degraded-mode fallback at the bootstrap level.

> **The required-packages registry is generic.** `REQUIRED_PACKAGES` in `_bootstrap/dependencies.py` is a single list of `(import_name, pip_name)` tuples — the readiness check, the announcement, the auto-install, the PEP 668 venv fallback, and the blocking gate all iterate over it. Today it holds the three tree-sitter grammars (the TS/JS AST checks); to make any other library a hard requirement, add one tuple. Stdlib and skill-internal modules aren't listed (always present); system tools the agent uses for review (git, gh) are out of scope (not pip-installable).
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
| `--verify` | Fast read-only check: exit 0 if already wired for this scope and Python is OK (nothing to do), non-zero if a full run is needed. Wires/installs nothing. Step 0 runs this first and only falls through to `--auto-install` when it's non-zero — so an already-set-up machine isn't re-bootstrapped on every skill invocation. |
| `--check` | Print the full readiness report; do not install or wire anything. |
| `--auto-install` | Install the required packages without the interactive confirm. Implied in non-TTY agent contexts (the install is mandatory, so it always proceeds there). |

There is no opt-out flag: the tree-sitter grammars are required. A host that genuinely can't install them is reported as a blocking issue, not silently downgraded.

## Idempotency

- First run: prints readiness, installs missing deps, wires hooks, links command, prints `Wired …`.
- Re-run with no changes: prints `already installed … No changes`.
- Re-run after skill upgrade: replaces the previous hook entry; unrelated `PreToolUse` entries are preserved.

## What to tell the user after it runs

- Reports `Wired` or `Updated` → tell the user to **restart the agent session** so the hooks activate.
- Reports `Install OK` for tree-sitter → also restart, so the TS/JS AST checks load.
- Exits with `Blocking issues:` (Python below 3.10, or the required tree-sitter grammars couldn't be installed) → surface the issue verbatim and ask the user to resolve it before proceeding. The hooks are **not** wired in this state and the skill is not ready.
- Exits with `cannot determine install scope` → the skill is invoked from outside a `.claude/skills/` tree. Point at `README.md`'s install command and skip Step 0; the rest of the skill still applies (rules enforced softly, no write-time blocking).
