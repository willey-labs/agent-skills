# Changelog — coding-standards skill

## 5.2.0 — 2026-10-10 — consent, opt-in judge, doc comments

### Install
- **The agent asks before a first install.** `--verify` reports `not installed` when
  nothing is wired; SKILL.md Step 0 then lists every change the install makes and
  waits for a yes. Repairing an existing install still runs without asking.
- **The comment judge is opt-in.** `--with-comment-judge` wires the `PostToolUse`
  recorder and `Stop` judge; `--without-comment-judge` removes them. With neither
  flag the judge stays as wired, and the session health check no longer counts an
  unwired judge as missing.
- The `SessionStart` health check re-runs the installer when any required hook is
  missing, and says so.
- Every `UserPromptSubmit` command ends with `; exit 0`, so a hook that cannot start
  never erases the user's prompt. Hook command paths are written in POSIX form, so
  Git Bash on Windows runs them.

### Rules
- **CM-007 blocks at write time**: a comment block a write adds may carry one line of
  prose. File headers and **doc comments directly above a declaration** (`/** */`,
  `///`, Go doc comments, Python function/class docstrings) are exempt.
- A per-prompt reminder (`SessionStart` + `UserPromptSubmit`) restates the comment
  default, CM-007 and the write-through-tools rule each turn.

### Precision
- Print-style calls in a program entry point (shebang, `__main__` guard, `main`
  function) no longer draw the FMT-005 advisory.
- The commented-out-code advisory ignores string literals and docstrings, reads `#`
  as a comment only in Python and PHP, and treats a closing bracket as a disabled
  block tail only when it is the whole comment.
- The filler-preamble advisory needs a colon after `Note`/`Important`/`Reminder`, so
  a wrapped line that opens on one of those nouns passes.

### Repository
- MIT `LICENSE` file.
- CI runs the hook suite on Linux and macOS (Python 3.10 and 3.12) and fails when the
  skill's own code draws any `review-files.py` finding.

## 5.1.0 — 2026-07-29 — comments: the default is none

The comment rules state their default explicitly and gain a write-time signal.

- **`comments.md` opens with the default: write no comment.** A file with zero comments
  is the normal outcome; a sentence earns its place only by carrying what the code
  cannot say. Code that seems to need explaining needs a better name or a smaller
  function instead.
- **CM-006 — no conversation in the source.** Bans what a chat leaves behind in a file:
  text addressed to a person, first-person deliberation, alternatives weighed inline,
  questions left in place, and `TODO`/`FIXME` with nothing tracking it. A rejected
  option earns a line only when it reads as a constraint.
- **`advise-comment-slop.py`** flags the mechanical tells on every Write/Edit across all
  source languages — emoji, exclamations, edit and history narration, filler preambles,
  banner comments, reader address, first-person deliberation, untracked `TODO`. Advisory
  only: comment prose can't be hard-blocked at the false-positive bar, so the judgement
  calls stay in review. Comments and Python docstrings are read with string literals
  blanked; linter pragmas, shebangs and SPDX lines are exempt.
- **Write mode names the rule up front.** The instruction to write no comments by
  default sits in SKILL.md's Write section, not only in the reference.

### The comment judge — a second reader, wired to two new events

Comment prose is the one rule family no pattern settles, and write-time self-review is
the weakest possible check on it: the pass that just wrote a paragraph of
self-justification will also approve it. So the judgement moved to a separate reader
that runs before a turn can end.

- **`record-touched-files.py` (PostToolUse)** ledgers each source file a turn wrote,
  outside the repo, skipping excluded, generated and non-source files.
- **`judge-comments.py` (Stop)** sends the comments on lines that turn changed —
  with the rules — to a separate `claude -p` call (one turn, no tools, no MCP, no
  hooks), and exits 2 on a delete or shorten verdict, which holds the turn open with
  the findings as the fix to apply. Trimming a comment can't change behaviour, so it
  needs no approval; a verdict that is genuinely wrong may be kept with the reason
  stated.
- **Bounds:** one short model call per turn that wrote source files, none when those
  files gained no comments; `sonnet` by default, `CODING_STANDARDS_JUDGE_MODEL` to
  change it; at most two holds per session; every failure path — no CLI, timeout,
  unparseable answer, an active Stop hook, the judge's own nested call — lets the turn
  end. Only changed lines are judged, so a legacy file's comments are never dragged in.
- **Wiring split by job (ST-008):** `_bootstrap/hook_registry.py` lists which script
  runs under which event, `hook_entries.py` builds one entry per event,
  `hook_identity.py` recognizes ours on re-run, and `settings.py` is left with reading,
  merging and writing settings.json.

### FMT-005 precision

The commented-out-code advisory no longer reads an English parenthetical as a disabled
call: a call form now requires its paren glued to the identifier. Assignments keep the
spaced form.

## 5.0.0 — 2026-06-13 — production-readiness hardening

An audit found gaps that let the enforcement layer pass code it should block, block
code it should pass, or fail silently. This release closes them and records the scope
decisions. Every fix ships with a regression test; the suite runs with one command
(`hooks/tests/run-all.py`) and reports DEGRADED rather than green when the
tree-sitter AST path can't be exercised.

### Enforcement correctness
- **`any` / `Any` bans now position-agnostic.** TypeScript catches `Record<string, any>`
  and other non-leading generic args, `type X = any` aliases, `satisfies`/`extends any`.
  Python catches PEP 585 lowercase generics (`dict[str, Any]`, `list[Any]`,
  `tuple[Any, ...]`) and PEP 604 pipe unions (`int | Any`).
- **God-file (ST-008) no longer evadable.** Arrow-function / function-expression
  `const`s count as behavioral declarations; Edit/MultiEdit are counted on the
  POST-edit content (an Edit that shrinks an over-limit file passes; one that grows
  past the limit blocks), and the block message names the full-file `Write` escape.
- **C# 12 primary constructors** (`class Foo(dep1, …, dep5)`) are FN-005-exempt like
  classic constructors and records.
- **Bundled catalog layouts stop tripping their own ST-005 hook.** A `utils/` folder is
  allowed when the project records `follows: feature-first` / `route-colocated` — derived
  from the adopted standard, folder-only (the `utils.ts` filename and `src/utils.ts`
  mega-file still block).
- **Enforcement can't die silently.** The managed venv now lives outside the skill dir
  (so `npx skills add` re-copies can't wipe it), a SessionStart health check loudly
  reports degraded enforcement, and `--verify` checks the wired hook scripts still exist.
- **Worker dispatch** carries `SKILL_DIR`, so review workers can resolve the reference
  files they're told to load.

### Coverage and precision
- Vue/Svelte `<script>` blocks now run the AST checks (FN-001/FN-005/OD-004), with line
  numbers aligned to the SFC.
- Cocos root-dir exclusion (`settings/`, `library/`, `temp/`) is gated on a Cocos layout,
  so it no longer blinds plain web/Django projects with a root `settings/`.
- `.coding-standards-ignore` writes are gated — every exemption needs a `# reason:` and is
  surfaced in a loud advisory (no silent self-exemption).
- Project-scope permissions go to `settings.local.json` (machine paths never committed);
  `additionalDirectories` is skipped on project scope.
- Hungarian (NM-006) now also covers TS class fields / interface members / object
  properties, and gains Go and Java/Kotlin checks.
- Go `any` catches return-tuple members and `map[any]V`.
- FN-005 carve-out covers FastAPI `Annotated[..., Depends()]` and pytest fixtures.
- Framework detection is file-type-aware (a `.php` in a Laravel + Vue repo resolves to
  `laravel`, not `vue-nuxt`).

### Polish and scope
- One shared extension set (`hooks/_languages.py`) — no more drift between hooks.
- `settings.example.json` matches the wired hook list (asserted by a test); MultiEdit
  line-number limitation documented; ST-005 mega-file ban extended to `app/`.
- Unity / Godot route to `unsupported` (engine override); Ruby/Rails, Rust, Swift/iOS,
  Flutter/Dart, Android declared explicitly unsupported for v5; the `lib/` folder-vs-file
  asymmetry is documented.
- `settings.py` split into `interpreter.py` + `permissions.py` to satisfy the skill's own
  ST-008 (the hooks dogfood on their own code).
