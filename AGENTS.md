# AGENTS.md

Instructions for agents working **on this repo** (not consuming the skill — for that, the skill activates itself).

This repo ships [Agent Skills](https://agentskills.io) for [Claude Code](https://claude.com/claude-code), [Cursor](https://cursor.com), [Codex](https://developers.openai.com/codex), [OpenCode](https://opencode.ai), and 50+ other agents listed in [`vercel-labs/skills`](https://github.com/vercel-labs/skills). The primary skill is `coding-standards`.

---

## Dogfood — the skill's rules apply to its own code

Every rule the `coding-standards` skill enforces against user code **also applies to the code in this repo**. The skill's hooks are wired into the maintainer's settings.json by `bootstrap.py`, so violations will be blocked at write time:

- No `utils.py`, `helpers.ts`, `common.go`, `misc.cs`, etc. (ST-005) — name every file by what it does. The bootstrap script is `bootstrap.py`, not `utils.py`.
- No `any` / `Any` / `interface{}` / `dynamic` / `mixed` — including in hooks and bootstrap.
- No Hungarian notation (`strName`, `arr_items`, ...).
- No function with 4+ positional args — group into a typed object/dataclass/struct.
- No deep imports past a folder's public API (ST-003).

If you find a rule annoying while editing this repo, fix the rule — don't bypass the hook.

---

## Repo layout

```
agent-skills/
  AGENTS.md                          ← this file (CLAUDE.md is a symlink to it)
  README.md                          ← user-facing install + usage
  skills/
    coding-standards/
      SKILL.md                       ← skill entrypoint; Step 0 runs bootstrap.py
      bootstrap.py                   ← deterministic hook installer
      hooks/                         ← 7 PreToolUse hooks (1 path-checker + 6 language content-checkers)
      references/
        common/                      ← language-agnostic rules (FN-*, NM-*, OD-*, ST-*, EH-*, FMT-*, DP-*)
        <framework>/structure.md     ← per-framework architecture rules
```

Paths inside `SKILL.md` are **relative to the SKILL.md file itself**, not the repo root — the skill is installed by symlink and must work from `~/.claude/skills/coding-standards/` or `<project>/.claude/skills/coding-standards/` identically.

---

## When adding a new hook

The hooks are stdlib-only Python (no third-party deps — they ship as-is). When extending them:

- **Precision over recall.** A regex pattern with a known false-positive rate above ~1% does not belong as a hard block — false positives are worse than missed catches. Document the trade-off in the hook file's docstring (`block-ts-violations.py` has examples — Hungarian single-char prefixes were dropped specifically because `aUser` is legitimate).
- **Strip strings and comments before matching content.** Every content hook has `strip_strings_and_comments()`; use it. The exception is import-path checks, which need raw lines (the path lives inside a string literal that the cleaner would blank out).
- **Always identify the rule code in the error message.** `"FN-005: function takes 4+ positional arguments"`, not `"too many args"`. The user reads the message, jumps to `references/common/functions.md#fn-005`, sees the worked example.
- **Exit 2 with stderr on block, 0 on pass.** Claude Code's PreToolUse contract.
- **Update `block-junk-paths.py`'s `JUNK_DRAWER_EXTS` if adding a new language.** ST-005 applies to every language; the path-checker is the universal entry point.

---

## When adding a new framework

1. Create `skills/coding-standards/references/<framework>/structure.md`.
2. The file MUST open with: `## Builds on common/structure.md` and name which universal rules it specializes or exempts.
3. Update the detection table in `SKILL.md` Step 1 with per-file signals (`package.json` keys, file extensions, config files at root). Be specific — `.ts` alone is not enough; pair with framework-distinctive markers.
4. Update the coverage table in `hooks/README.md` to point at the right language hook.
5. If the framework brings a new language not yet covered (e.g. Ruby, Elixir), ship a `block-<lang>-violations.py` hook with at minimum: arg count, language's `any` equivalent, and language's Hungarian convention. Stdlib only.

---

## Testing the hooks — the cardinal rule

**Never test against `~/.claude/settings.json`.** The bootstrap script edits real settings; an absent `HOME` override during a test will modify the maintainer's machine.

Sandbox pattern:

```bash
SANDBOX=$(mktemp -d)
export HOME="$SANDBOX/home"
mkdir -p "$HOME/.claude/skills"
ln -sf /path/to/repo/skills/coding-standards "$HOME/.claude/skills/coding-standards"

# Now run bootstrap.py / hooks safely; they target $SANDBOX/home/.claude/

rm -rf "$SANDBOX"
```

For per-hook regression tests: feed JSON payloads via stdin, check exit code + stderr.

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"/r/a.py","content":"def f(a,b,c,d): pass"}}' \
  | python3 hooks/block-py-violations.py
# expect exit 2 with FN-005 message
```

---

## Bootstrap detection logic — don't break it

`bootstrap.py` uses `Path(__file__).absolute()` (NOT `.resolve()`). The skill is symlinked from a canonical install location into `~/.claude/skills/<name>/` or `<project>/.claude/skills/<name>/`. Following the symlink (resolve) lands on the canonical path, which has no `.claude` ancestor — scope detection breaks and the script either refuses (good) or writes to the wrong settings.json (bad).

If you touch the scope-detection code, re-run the 6-test matrix:

1. Project install, no settings.json → wires correctly with `${CLAUDE_PROJECT_DIR}` paths.
2. Re-run → noop.
3. Existing unrelated `PreToolUse` hook + other settings keys → all preserved.
4. Global install → wires with absolute paths to `~/.claude/settings.json`.
5. Invoked outside any `.claude/` tree → refuses cleanly (does not write).
6. Upgrade — older entry of ours → replaced, unrelated entries kept.

---

## What this repo does NOT cover

- Test design (TDD/BDD/mutation testing).
- Performance tuning (use a profiler).
- Security review (use the `security-review` skill).
- UI/UX visual review (separate skill).
- Mechanical violations the user's project linter catches (`tsc`, ESLint, `ruff`, `golangci-lint`, PHPStan, Roslyn analyzers). The hooks here cover what regex can do cleanly at PreToolUse; the linter catches the rest at commit time.

---

## Commit + PR conventions

- Conventional commits style is fine but not required. Prefer concise present-tense subjects: `add block-jvm-violations.py`, `fix Hungarian false positive on aUser`.
- Each PR should pass its own hooks. If the hooks block your work, the rule wins — fix the code, not the rule (unless the rule is genuinely wrong, in which case fix the rule and add a test case).
- Keep `hooks/README.md` and the coverage table in sync with the actual hook files.
