# AGENTS.md

Instructions for agents editing this repo. `CLAUDE.md` is a symlink to this file.

The repo ships two [Agent Skills](https://agentskills.io): `coding-standards` (code rules, enforced by write-time hooks) and `writing-standards` (document rules, delivered as a reminder injected on `SessionStart` and `UserPromptSubmit`).

## The skill's rules apply to this repo

The maintainer's settings wire the `coding-standards` hooks, so a violating write here is blocked like anywhere else: no junk-drawer file names (ST-005), no `any`/`Any`/`interface{}`/`dynamic`/`mixed`, no Hungarian notation, no 4+ positional arguments, no deep imports (ST-003). If a rule is wrong, fix the rule and add a test case. Never bypass the hook.

## Layout

```
skills/
  coding-standards/
    SKILL.md        entry point; Step 0 runs bootstrap.py
    bootstrap.py    installer; must stay at the skill root
    _bootstrap/     installer internals
    hooks/          enforcement hooks, shared helpers (_*.py), tests/
    references/     common/ rules + <framework>/structure.md
    workers/        prompts for the review pipeline's agents
    evals/          false-block-rate and block-recovery evals for the hooks
  writing-standards/
    SKILL.md, bootstrap.py, _bootstrap/, hooks/, references/common/
evals/              with/without-skill agent evals (`claude plugin eval .`)
.github/workflows/  CI: hook suite on Linux and macOS, plus the skill linting itself
```

Paths inside a `SKILL.md` are relative to that `SKILL.md`. The skill is installed by symlink and must work from `~/.claude/skills/<name>/` and `<project>/.claude/skills/<name>/` alike.

## Adding a hook

- Register the script's basename in `_bootstrap/hook_registry.py` only, under its event: `HOOK_FILES` (PreToolUse), `POST_TOOL_USE_FILES`, `STOP_FILES`. Entry builders, recognizers, `hooks/settings.example.json` and the config-sync test all read these lists. `PostToolUse` and `Stop` belong to the opt-in comment judge (`COMMENT_JUDGE_EVENTS` in `_bootstrap/hook_identity.py`): their scripts are required only once the judge is wired.
- Bootstrap never changes a user's machine unasked: SKILL.md Step 0 asks before a first install, and anything with a running cost is opt-in.
- Hooks are stdlib-only Python. A required third-party package goes in `_bootstrap/dependencies.py`'s `REQUIRED_PACKAGES` only, as one `(import_name, pip_name)` tuple; raise `MIN_PYTHON` there if it needs a newer Python. Prefer a regex or `ast` check over a new dependency.
- Route every path written into a hook command through `command_path` (`_bootstrap/paths.py`). Git Bash on Windows eats the backslashes of a native path. Paths Claude Code reads directly, such as `permissions.additionalDirectories`, stay native. `hooks/tests/test-windows-command-paths.py` guards this.
- Precision over recall: a pattern with a false-positive rate above ~1% must not hard-block. Record the trade-off in the hook's docstring.
- Strip strings and comments before matching content (`strip_strings_and_comments()`). Exceptions: import-path checks, and `block-swallowed-errors.py`, where a comment inside an empty `catch` is the allowed EH-002 escape.
- Put the rule code in every message: `FN-005: function takes 4+ positional arguments`.
- PreToolUse: exit 2 with stderr to block, exit 0 to pass. A real but imprecise signal exits 0 with an advisory, and the hook is named `advise-*`.
- Emit advisories through `advise()`/`advisory_message()` in `_hook_run.py`; stderr from an exit-0 hook reaches only the debug log. Read them back with `advisory_text()`.
- End every `UserPromptSubmit` command with `; exit 0`. Exit 2 there erases the user's prompt, and a command the shell cannot start exits 2 before the script runs. Other events keep their exit codes. `hooks/tests/test-prompt-hook-fail-open.py` guards both installers.
- A new language's extension goes in `hooks/_languages.py`: `SOURCE_EXTENSIONS` for the path and god-file checks, `CONTENT_HOOK_EXTENSIONS` once its content hook ships.

## Adding a framework

1. Create `skills/coding-standards/references/<framework>/structure.md`, opening with `## Builds on common/structure.md` and naming the universal rules it specializes or exempts.
2. Add a row to the detection table in `SKILL.md` Step 3. Pair file extensions with framework-specific markers (`package.json` keys, root config files); `.ts` alone is not a signal.
3. Update the coverage table in `hooks/README.md`.
4. For a new language, ship `block-<lang>-violations.py` covering at least argument count, the language's `any`, and its Hungarian convention.

## Testing

Never run bootstrap or hooks against the real `~/.claude/settings.json`. Point `HOME` at a sandbox first:

```bash
SANDBOX=$(mktemp -d)
export HOME="$SANDBOX/home"
mkdir -p "$HOME/.claude/skills"
ln -sf /path/to/repo/skills/coding-standards "$HOME/.claude/skills/coding-standards"
# run bootstrap.py / hooks here
rm -rf "$SANDBOX"
```

Bootstrap tests build that sandbox through `hooks/tests/bootstrap_sandbox.py`.

Run the suite with the interpreter that has tree-sitter (the bootstrap venv): `hooks/tests/run-all.py`. Exit 0 is pass, 1 is a failure, 2 means the AST checks were skipped. CI also fails when `review-files.py` reports any finding on the repo's own Python.

Test a single hook by piping a payload:

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"/r/a.py","content":"def f(a,b,c,d): pass"}}' \
  | python3 hooks/block-py-violations.py   # exit 2, FN-005
```

## Bootstrap scope detection

Scope comes from the install path, which carries the `.claude/skills/` segment. Anchor on `Path(...).absolute()`, never `.resolve()`: resolving follows the symlink to the canonical checkout, which has no `.claude` ancestor. `_bootstrap/paths.py` takes the anchor from the main script (`sys.modules["__main__"].__file__`, falling back to `sys.argv[0]`), because Python keeps the symlinked path only for the main script. `bootstrap.py` therefore stays at the skill root; moving it shifts `SKILL_DIR` and misplaces `hooks/`, `commands/` and the permission grants.

After touching scope detection, run `hooks/tests/test-bootstrap-matrix.py`. It automates the 6-test matrix:

1. Project install, no settings.json → wired with `${CLAUDE_PROJECT_DIR}` paths.
2. Re-run → noop.
3. Unrelated `PreToolUse` hook and other settings keys → preserved.
4. Global install → wired with absolute paths into `~/.claude/settings.json`.
5. Run outside any `.claude/` tree → refuses without writing.
6. Upgrade from an older entry of ours → replaced, unrelated entries kept.

The same test checks that the comment judge is off by default, follows `--with-comment-judge` / `--without-comment-judge`, and survives a re-run without either flag.

## Out of scope

Test design, performance tuning, security review, visual UI review, and anything the project's own linter (`tsc`, ESLint, `ruff`, `golangci-lint`, PHPStan, Roslyn) already catches.

## Commits and PRs

- Short present-tense subjects: `add block-jvm-violations.py`, `fix Hungarian false positive on aUser`. Conventional commits are optional.
- Every PR passes its own hooks.
- Keep `hooks/README.md` and its coverage table in sync with the hook files.
