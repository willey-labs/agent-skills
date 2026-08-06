# AGENTS.md

Instructions for agents working **on this repo** (not consuming the skill — for that, the skill activates itself).

This repo ships [Agent Skills](https://agentskills.io) for [Claude Code](https://claude.com/claude-code), [Cursor](https://cursor.com), [Codex](https://developers.openai.com/codex), [OpenCode](https://opencode.ai), and 50+ other agents supported by the `skills` CLI. The primary skill is `coding-standards`; a companion, `writing-standards`, governs documents (it injects a reminder via `SessionStart` + `UserPromptSubmit` hooks rather than blocking writes).

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
      bootstrap.py                   ← installer entry point + orchestrator (stays at root: SKILL.md + the slash command invoke it by this exact path)
      _bootstrap/                    ← installer internals (ST-001/ST-004 package): paths, dependencies (REQUIRED_PACKAGES registry + presence checks), readiness, install (mandatory deps + venv fallback), scope (detection + ignore template), hook_registry (which script runs under which event — the one place a new script is listed), hook_entries (one entry builder per event), hook_identity (recognizing our own entries on re-run, and reporting which registered scripts the wiring is missing), verify (the read-only `--verify` answer: fails a stale install as well as a broken one, and every failure names the command that repairs it), settings (settings.json read/merge/write + permissions), command (/coding-standards slash-command install, symlink-or-copy)
      hooks/                         ← 13 PreToolUse hooks (1 path-checker + 6 language content-checkers + block-swallowed-errors [EH-002, cross-language] + block-debug-artifacts [FMT-005, cross-language: blocks debugger/dd/pdb, advises on print residue + commented-out code] + block-god-file [ST-008: blocks on behavioral-decl count, advises on size/flat-folder] + advise-comment-slop [CM-004/005/006, cross-language, advisory only: emoji, exclamations, edit/history narration, filler preambles, banners, reader address, first-person deliberation, untracked TODO — prose judgement stays in review] + block-added-comments [CM-007, cross-language: refuses a comment block the write ADDS that runs past one prose line; subtracts the prose already on disk, so old paragraphs are never re-judged — that subtraction is what makes length a hard block instead of an advisory; file-header blocks and machine pragmas exempt; limit via CODING_STANDARDS_MAX_COMMENT_LINES] + block-structure-file-violations [keeps .coding-standards-structure to placement only]); THREE further events carry the comment judge and the reminder — record-touched-files.py [PostToolUse: ledgers the source files a turn wrote] + judge-comments.py [Stop: sends that turn's comments to a separate `claude -p` call and exits 2 to hold the turn open until delete/shorten verdicts are applied; fails open on every error, max 2 holds per session] + inject-coding-standards.py [SessionStart + UserPromptSubmit: prints the comment default, CM-007 and the write-through-tools rule to stdout so a rule read once isn't buried by the time code is written; NEVER exits non-zero — that would block the user's prompt]; comment extraction shared by all three comment hooks in _comment_scan.py, block selection in _comment_blocks.py, the model call in _comment_judge.py, the session ledger in _touched_ledger.py; block-ts delegates regex to itself, imports/ST-003 to _ts_imports.py, AST to _ts_node_checks.py via _ts_ast.py; block-py to _py_ast.py; all language hooks share the gate/emit plumbing (incl. multi-line signature join) in _hook_run.py
      references/
        common/                      ← language-agnostic rules (FN-*, NM-*, OD-*, ST-*, EH-*, FMT-*, CM-*, DP-*)
        <framework>/structure.md     ← per-framework architecture rules
    writing-standards/               ← companion skill: standards for DOCUMENTS, not code
      SKILL.md                       ← entrypoint; Step 0 runs bootstrap.py --verify then bootstrap.py
      bootstrap.py                   ← wires SessionStart + UserPromptSubmit hooks into settings.json (stays at root: SKILL.md invokes it by this exact path; _bootstrap/paths anchors scope detection on it)
      _bootstrap/                    ← installer internals, trimmed copy of coding-standards' (no deps/venv — the hook is stdlib-only): paths (symlink-preserving anchor), scope (project/global detection), settings (settings.json merge, recognizes our entry by the inject-script basename)
      hooks/
        inject-writing-standards.py  ← prints the reminder to stdout (→ Claude context); wired to BOTH events. NEVER exits non-zero — a non-zero UserPromptSubmit hook would block the user's prompt
      references/
        common/                      ← source-to-deliverable.md (SD-*) + anti-slop.md (SL-*)
```

Paths inside `SKILL.md` are **relative to the SKILL.md file itself**, not the repo root — the skill is installed by symlink and must work from `~/.claude/skills/coding-standards/` or `<project>/.claude/skills/coding-standards/` identically.

---

## When adding a new hook

The hooks are stdlib-only Python, with one exception: `block-ts-violations.py` (via its sibling `hooks/_ts_ast.py`) requires `tree-sitter` for its AST checks. That dep (and any future one) is declared in `_bootstrap/dependencies.py`'s `REQUIRED_PACKAGES` and is **mandatory** — `bootstrap.py` checks, announces, auto-installs (with a PEP 668 venv fallback), and refuses to wire the hooks until every entry loads. When extending the hooks:

- **A new script's basename goes in `_bootstrap/hook_registry.py`, nowhere else** — under the list for the event it runs on (`HOOK_FILES` for PreToolUse, `POST_TOOL_USE_FILES`, `STOP_FILES`). The entry builders, the recognizers, the example settings and the config-sync test all read those lists.
- **A new third-party dependency goes in `_bootstrap/dependencies.py`'s `REQUIRED_PACKAGES`, nowhere else.** Add one `(import_name, pip_name)` tuple; the readiness check, announcement, auto-install, venv fallback, and blocking gate all iterate over that list — no special-casing. If the new package needs a newer Python, bump `MIN_PYTHON` (also in `_bootstrap/dependencies.py`) too. Prefer stdlib first: a regex/`ast`-based check with no dependency is always better than adding one.
- **Any path written into a hook command goes through `command_path` (`_bootstrap/paths.py`).** Hook commands are executed by a shell — Git Bash on Windows — which consumes the backslashes of a native Windows path as escapes and leaves the command pointing at a mangled filename. Both skills' `_bootstrap` packages export it; `hooks/tests/test-windows-command-paths.py` guards every call site. Filesystem paths that Claude Code consumes directly (`permissions.additionalDirectories`) stay native.
- **Precision over recall.** A regex pattern with a known false-positive rate above ~1% does not belong as a hard block — false positives are worse than missed catches. Document the trade-off in the hook file's docstring (`block-ts-violations.py` has examples — Hungarian single-char prefixes were dropped specifically because `aUser` is legitimate).
- **Strip strings and comments before matching content.** Every content hook has `strip_strings_and_comments()`; use it (`block-god-file.py` strips with its own `strip_noncode()` before the column-0 declaration count, so embedded code samples aren't miscounted). Two deliberate exceptions need raw lines: import-path checks (the path lives inside a string literal the cleaner would blank out) and `block-swallowed-errors.py` (a comment inside an otherwise-empty `catch`/`except` IS the documented EH-002 escape, so the comment must stay visible to the matcher).
- **Always identify the rule code in the error message.** `"FN-005: function takes 4+ positional arguments"`, not `"too many args"`. The user reads the message, jumps to `references/common/functions.md#fn-005`, sees the worked example.
- **Exit 2 with stderr on block, 0 on pass.** Claude Code's PreToolUse contract. When a rule's signal is real but not precise enough to refuse a write — raw size, print residue, comment prose — exit 0 and emit the finding as an advisory instead of dropping the check. Name the hook for what it does: a hook that never blocks is `advise-*`, not `block-*`.
- **An advisory goes out through `advise()`/`advisory_message()` (`_hook_run.py`), never `sys.stderr`.** Stderr reaches Claude only on exit 2; from an exit-0 hook it lands in the debug log and nowhere else, so an advisory written there corrects nobody. Those helpers wrap it as `hookSpecificOutput.additionalContext` on stdout, which Claude Code delivers with the tool result. Anything reading a hook's findings back — the reviewer CLI, the test harness — pairs with them via `advisory_text()`.
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

Scope detection anchors on `Path(...).absolute()` (NOT `.resolve()`). The skill is symlinked from a canonical install location into `~/.claude/skills/<name>/` or `<project>/.claude/skills/<name>/`. Following the symlink (resolve) lands on the canonical path, which has no `.claude` ancestor — scope detection breaks and the script either refuses (good) or writes to the wrong settings.json (bad).

**The anchor lives in `_bootstrap/paths.py` and MUST come from the main script, not the module.** It computes `SCRIPT_PATH`/`SKILL_DIR` from `sys.modules["__main__"].__file__` (falling back to `sys.argv[0]`) — i.e. `bootstrap.py` as invoked. This is load-bearing two ways: (1) Python preserves the symlinked path for the **main script's** `__file__` but **resolves the symlink for an imported module's** `__file__`, so anchoring on `paths.py`'s own `__file__` would land on the canonical path and break scope detection; (2) `bootstrap.py` MUST stay at the skill root — `SKILL_DIR` is its parent, and moving it into the package would shift `SKILL_DIR` down a level and misplace `hooks/`, `commands/`, and the permission grants. Both are caught by Test 1 of the matrix below (it wires to the wrong location). The installer logic lives in the `_bootstrap/` package (`paths`, `dependencies`, `readiness`, `install`, `scope`, `settings`) with `bootstrap.py` as the orchestrator (ST-008/ST-004); scope detection itself is in `_bootstrap/scope.py`.

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
