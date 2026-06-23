# Changelog — coding-standards skill

## 5.0.0 — 2026-06-13 — production-readiness hardening

A full audit (see the repo-root `AUDIT.md`) found gaps that let the enforcement
layer pass code it should block, block code it should pass, or fail silently. This
release closes every P0 and P1, lands the P2 polish, and records the P3 scope
decisions. Every fix ships with a regression test; the suite runs with one command
(`hooks/tests/run-all.py`) and reports DEGRADED rather than green when the
tree-sitter AST path can't be exercised.

### Enforcement correctness (P0)
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

### Coverage and precision (P1)
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

### Polish (P2) and scope (P3)
- One shared extension set (`hooks/_languages.py`) — no more drift between hooks.
- `settings.example.json` matches the wired hook list (asserted by a test); MultiEdit
  line-number limitation documented; ST-005 mega-file ban extended to `app/`.
- Unity / Godot route to `unsupported` (engine override); Ruby/Rails, Rust, Swift/iOS,
  Flutter/Dart, Android declared explicitly unsupported for v5; the `lib/` folder-vs-file
  asymmetry is documented.
- `settings.py` split into `interpreter.py` + `permissions.py` to satisfy the skill's own
  ST-008 (the hooks dogfood on their own code).
