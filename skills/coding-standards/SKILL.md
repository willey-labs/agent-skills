---
name: coding-standards
description: >
  Coding standards for writing, editing, and reviewing code. Routes to language/framework-specific
  rules (Next.js, NestJS, Laravel, vanilla JS/TS, NativeScript, React Native/Expo, C#/.NET,
  Node Express/Fastify, Cocos Creator, Vue/Nuxt, Spring Boot, Django, FastAPI, Flask, Go HTTP)
  PLUS universal clean-code rules (functions, naming, objects/data, formatting, error handling,
  SOLID/KISS/DRY, universal structural rules) that apply to every language. Consult before any
  code change. Use when the user says "write a component", "add an endpoint", "refactor this",
  "review this diff/PR", or "is this clean?". Make sure to consult this skill for ANY code
  authoring or review task, even when the user does not explicitly ask for "standards" — every
  write/edit/review must comply.
license: MIT
metadata:
  author: willey-lab
  version: "4.0.0"
---

# Coding Standards

Every line of code you write, edit, or review must comply with these rules.

The rules are split in two:

- **Universal rules** in `references/common/` — clean-code principles that apply regardless of language. They govern the *inside* of every function, class, and module.
- **Per-framework rules** in `references/<framework>/` — folder layout, file organization, and framework-specific patterns. They govern the *outside* — where files live and what folders mean.

You apply **common + one framework** on every task. Never apply two frameworks at once.

---

## Skill location

All paths in this document are **relative to this SKILL.md file**. `references/common/functions.md` means the file under the `references/common/` subdirectory next to this SKILL.md. This works regardless of where the skill is installed.

---

## Step 0 — Bootstrap the enforcement hooks + readiness check (run once per skill install)

**Run this exactly once the first time the skill activates in any new session, scope, or after a skill update.** It does:

1. **Readiness check** — Python version (3.9+), Python command (`python` vs `python3`), pip availability, virtualenv detection, platform (Windows / macOS / Linux), tree-sitter package availability.
2. **Auto-install missing tree-sitter packages** — when invoked with `--auto-install` (recommended for agent contexts; the bootstrap can't prompt the user from a non-TTY).
3. **Wire PreToolUse hooks** into the correct `settings.json` (project vs global is auto-detected from the SKILL.md install path).
4. **Symlink `/coding-standards` slash command** into `.claude/commands/`.

### How to invoke from the agent (non-TTY context)

```bash
python3 <skill-dir>/bootstrap.py --auto-install
```

or, if `python3` isn't on PATH (some Windows installs):

```bash
python <skill-dir>/bootstrap.py --auto-install
```

The bootstrap detects the right Python command at runtime and writes it into `settings.json`, so hook commands work cross-platform.

### How to invoke interactively (user shell)

```bash
python3 <skill-dir>/bootstrap.py
```

Without flags, the bootstrap prompts the user for tree-sitter install confirmation when stdin is a TTY.

### Flags

| Flag | Purpose |
|---|---|
| `--check` | Only report readiness; do not install or wire anything. |
| `--auto-install` | Install missing tree-sitter without prompting. Use from agent context. |
| `--skip-install` | Skip the tree-sitter install offer entirely. |

### Idempotency

- First run: prints readiness, installs missing deps, wires hooks, links command, prints `Wired …`.
- Re-run with no changes: prints `already installed … No changes`.
- Re-run after skill upgrade: replaces previous hook entry; unrelated `PreToolUse` entries are preserved.

### What to tell the user after Step 0

If bootstrap reports `Wired` or `Updated`, tell the user: **restart the agent session** so the hooks activate.

If bootstrap reports `Install OK` for tree-sitter packages, also restart so the TS/JS AST checks load.

If bootstrap exits with `Blocking issues:` (Python too old, etc.), surface the issue verbatim and ask the user to resolve before proceeding.

If bootstrap exits with `cannot determine install scope`, the skill is invoked from outside a `.claude/skills/` tree — point at `README.md` install command and skip Step 0; the rest of the skill still applies (rules enforced softly, no write-time blocking).

---

## Step 0.4 — Exclusion check (always)

Before applying any rule to a file, check whether it's **excluded**. Excluded files are owned by third-party tooling, not by the user — modifying them defeats the upgrade path or churns generated code. Skip them silently.

A file is excluded if **any** of:

1. **Its path matches a built-in default pattern.** Common cases:
   - `**/node_modules/**`, `**/vendor/**`, `**/bower_components/**` — installed deps
   - `**/components/ui/**` (and monorepo variants like `packages/components/ui/**`, `apps/web/src/components/ui/**`) — shadcn/ui generated components, owned by the shadcn CLI
   - `**/prisma/migrations/**`, `**/drizzle/migrations/**`, `**/alembic/versions/**`, `**/migrations/[0-9][0-9][0-9][0-9]_*.py` (Django) — ORM-generated migrations
   - `**/generated/**`, `**/__generated__/**`, `**/*.gen.ts`, `**/*.generated.tsx`, `**/zz_generated.*`, `**/*_pb.go`, `**/*_grpc.pb.go` — codegen output
   - `**/dist/**`, `**/build/**`, `**/.next/**`, `**/.nuxt/**`, `**/.svelte-kit/**`, `**/target/**`, `**/bin/**`, `**/obj/**` — build outputs
   - `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`, `**/composer.lock`, `**/Cargo.lock`, `**/go.sum`, `**/poetry.lock`, `**/uv.lock` — lock files
   - Full list in `hooks/_exclusions.py` → `DEFAULT_EXCLUSIONS`
2. **The file content has a generation marker** in the first 10 lines: `@generated`, `DO NOT EDIT`, `automatically generated`, `Code generated by`, `@autogenerated`, `@codegen`, `@nocheck`.
3. **The project has a `.coding-standards-ignore` file** at its root with a matching gitignore-style pattern.

The hooks already check this — they exit 0 silently on excluded files. **You** (the agent/orchestrator/workers) must do the same: when asked to write or review code, check the target path against `hooks/_exclusions.py`'s `is_excluded_path()` (or apply the same rules) and refuse to modify excluded files. If the user explicitly asks to modify an excluded file, **ask once for confirmation** — explain that the file is normally owned by the tool that generated it, and modification will be lost on re-generation. Proceed only after explicit consent.

For the orchestrator pipeline: filter the target file list through `is_excluded_path()` BEFORE dispatching to Worker 1. Excluded files never reach the workers.

---

## Step 0.5 — Pick a mode if the user didn't (contextless activation only)

**Skip this step** if the user's message already names a concrete task — "write X", "refactor Y", "review this PR/diff", "is this clean?", "audit Z", "what does FN-005 mean?". Those phrases ARE the mode; proceed to Step 1.

**Trigger this step** only when the skill activated without a clear task in the same turn:
- User typed `/coding-standards` with no arguments (see `commands/coding-standards.md`),
- User said "what does this skill do?" / "tell me about coding standards",
- User's message is too generic to infer mode ("help me with my code", "check my project").

When triggered, invoke the `AskUserQuestion` tool with EXACTLY this payload (do not paraphrase the descriptions — they are the deterministic UX):

```
question:    "What do you want to do with the coding-standards skill?"
header:      "Mode"
multiSelect: false
options:
  - label:       "Write code that follows these rules"
    description: "I'll detect the framework from your project, load the matching
                  references, and apply the rules as I write. Hard violations get
                  blocked at write time by the installed hooks."

  - label:       "Check existing code against these rules"
    description: "Point me at a file, folder, or diff and I'll report violations.
                  PASS / FAIL / SKIPPED per applicable rule with file:line citations,
                  grouped by must-fix / should-fix / consider."

  - label:       "Show me the rules"
    description: "Guided tour of the rule families (FN-*, NM-*, OD-*, ST-*, EH-*,
                  FMT-*, DP-*) plus the detected framework. Cite rule codes with
                  worked examples from the reference files."
```

After the answer:
- **Write code…** → Step 1 → Step 2 → Write mode.
- **Check existing code…** → ask the user *what* to check (file, folder, diff command, PR number) → Step 1 (per-file) → Step 2 → Review mode (use the strict PASS/FAIL walkthrough from this SKILL.md's Review section).
- **Show me the rules** → Step 1 (detect framework once) → Step 2 (load all refs) → present a one-screen index of rule codes and wait for follow-up questions.

**Invariants:**
- Never invoke this step twice in a session — once mode is set, it stays set.
- Never invoke it when the user has named a task — that's an annoying false ask.
- The four exact words "Write code that follows these rules", "Check existing code against these rules", "Show me the rules" are part of the contract; the slash command and skill activation must produce identical option text.

---

## Step 1 — Detect the framework

Look at the file you're about to write/edit/review. Determine which framework folder applies using the signals below. **Stop at the first match.**

| Framework key | Detection signals (any of these) |
|---|---|
| `nextjs` | `next.config.{js,ts,mjs}` at repo root **or** `next` in `package.json` dependencies **or** the file lives under `app/` or `pages/` next to that config |
| `react-native` | `expo`, `react-native`, or `@expo/*` in `package.json` **or** `app.json` with `"expo"` key **or** `metro.config.js` |
| `nativescript` | `nativescript.config.{js,ts}` or `nativescript` in `package.json` **or** a `.xml` file paired with a `.ts` page |
| `cocos-creator` | `assets/` + `settings/` + (`library/` or `temp/` in `.gitignore`) at repo root **or** `cc` / `cocos-creator` import in a `.ts` file **or** `.scene` / `.prefab` files in the project |
| `vue-nuxt` | `vue` or `nuxt` in `package.json` **or** `nuxt.config.{ts,js}` at repo root **or** `.vue` files in the project |
| `nestjs` | `@nestjs/*` in `package.json` **or** the file matches `*.module.ts`, `*.controller.ts`, `*.service.ts` with NestJS decorator imports |
| `node-express` | `express` or `fastify` in `package.json` **and** no NestJS — backend Node without a framework on top |
| `laravel` | `composer.json` with `laravel/framework` **or** an `artisan` file at the repo root **or** the file is `.php` under `app/` |
| `csharp` | `*.csproj`, `*.sln`, `*.cs` files |
| `spring-boot` | `pom.xml` with `spring-boot-starter-*` **or** `build.gradle{,.kts}` with `org.springframework.boot` plugin **or** `@SpringBootApplication` in a `.java`/`.kt` file |
| `django` | `manage.py` + `settings.py` at repo root **or** `django` in `pyproject.toml` / `requirements.txt` |
| `fastapi` | `fastapi` in `pyproject.toml` / `requirements.txt` **or** `from fastapi import FastAPI` in a `.py` file |
| `flask` | `flask` in `pyproject.toml` / `requirements.txt` **or** `from flask import Flask` **and** not Django/FastAPI |
| `go-http` | `go.mod` at repo root **and** any of `gin-gonic/gin`, `labstack/echo`, `gofiber/fiber`, `go-chi/chi`, `gorilla/mux` in the module graph — or net/http with handler-based routing |
| `vanilla-js` | Plain `.ts` / `.js` files that fit none of the above (libraries, CLIs, scripts, browser projects without a framework) |

**If two could apply** (rare), pick the more specific one. A `.ts` file inside a NestJS project is `nestjs`, not `vanilla-js`. A `.tsx` file inside a Next.js project is `nextjs`, not `react-native`, even if the file imports React. A `.vue` file inside a Nuxt project is `vue-nuxt`.

**Monorepos with multiple frameworks** (frontend Next.js + backend NestJS + mobile React Native in one repo) are common and supported. **Pick the framework by the file you're editing, not the repo as a whole.** Editing `apps/web/src/checkout/...` → `nextjs`. Editing `apps/api/src/orders/...` in the same repo → `nestjs`. Editing a `.tsx` file under `apps/mobile/` → `react-native`. The detection signals above all apply per-file or per-subtree; walk up from the file until one matches.

**Generic libraries with no framework signals** (a utility npm package, a CLI tool, a small Python script not tied to any web framework) default to the corresponding "no-framework" entry: `vanilla-js` for JS/TS, or — if Python — the closest fit (`flask`/`fastapi`/`django`) doesn't apply, so fall back to the universal rules in `common/` only. The Python framework files do **not** cover plain library code.

**If you cannot tell**, ask the user once — don't guess across frameworks.

---

## Step 1.5 — Pick execution shape: orchestrator pipeline vs inline

You have two execution shapes for Write and Review modes. Pick deterministically:

| Trigger | Execution shape |
|---|---|
| Task scope = single file edit (≤30 lines change), OR single function refactor, OR Q&A about a rule | **Inline.** You (the main agent) do the work yourself. Skip Step 2.X and continue with Step 2 (load all references) → Step 3 (apply rules). |
| Task scope = 2+ files, OR a new feature/use case, OR a diff/PR review, OR explicit `--thorough` flag, OR explicit `/coding-standards` slash command | **Orchestrator pipeline.** You become the orchestrator and dispatch to workers. Continue with Step 2.O (orchestrator). |
| `Agent` tool is NOT available in this host | Fall back to **inline** regardless of scope. |

**Default to inline when uncertain.** The pipeline is for non-trivial work where the latency cost is justified by the comprehensiveness gain.

---

## Step 2.O — Orchestrator pipeline (when picked above)

You (the main agent) are now the **orchestrator**. You do not apply rules yourself; you coordinate three sequential workers. Workers never write to disk — you do the final Write at the end. This guarantees hooks fire exactly once on the final code.

### Worker roster

| Worker | Owns | Brief file |
|---|---|---|
| **Worker 1 — Structure & Architecture** | ST-*, OD-001, OD-002, OD-004, OD-005, DP-001 to DP-005, `<framework>/structure.md` | `workers/worker-1-structure.md` |
| **Worker 2 — Code Quality (line level)** | FN-001 to FN-009, NM-*, OD-003, FMT-* | `workers/worker-2-quality.md` |
| **Worker 3 — Failure Handling** | EH-*, FN-010 | `workers/worker-3-failure.md` |

Cross-cutting principles (DP-006 KISS, DP-007 DRY, FN-011) are applied **per-domain** by each worker as a lens — no single worker owns them.

### Pipeline shape

**Write mode:**
```
User task
  → Worker 1 outputs file skeletons (paths, imports, signatures, placeholder bodies)
  → Worker 2 outputs files with function bodies, names, formatting, Demeter fixes
  → Worker 3 outputs final files with error boundaries, async safety, idiomatic failure
  → Orchestrator writes files (one Write call per file; hooks fire here on final code)
```

**Review mode:**
```
User task (diff/PR/file)
  → Worker 1 outputs findings JSON (no code changes)
  → Worker 2 outputs findings JSON
  → Worker 3 outputs findings JSON
  → Orchestrator concatenates, sorts by severity, presents unified report
```

### How to dispatch a worker

For each worker N in {1, 2, 3}:

1. **Read the brief**: `workers/worker-N-<name>.md`. The frontmatter tells you `owns_rules`, `applies_as_lens`, `must_not_touch`. The body is the prompt template.
2. **Construct the dispatch prompt** by combining:
   - The full body of the worker's brief file
   - A trailing block:
     ```
     === INPUT ===
     TASK: <user's original task verbatim>
     FRAMEWORK: <detected framework key from Step 1>
     MODE: write | review
     WORKER_<N-1>_OUTPUT: <previous worker's JSON, omit for Worker 1>
     ```
3. **Call the `Agent` tool** with:
   - `subagent_type: "general-purpose"`
   - `description: "coding-standards worker <N>"`
   - `prompt`: the constructed prompt
4. **Parse the worker's JSON output.** If parsing fails:
   - Retry once with a clarifying message: "Your previous response was not valid JSON. Return ONLY the JSON object specified in the brief."
   - If still failing, fall back to inline (load all references yourself, do the work, write files).
5. **Validate the output**:
   - Worker only modified files it had authority over (check `must_not_touch`).
   - Worker's `changes_made` / `decisions` / `error_handling_added` cite a rule code it owns.
   - Worker did not introduce abstractions outside its rule list (no new Strategy patterns from Worker 2; no new layers from Worker 3).
6. **If validation fails**, redispatch the worker with the specific violation noted. After one retry, fall back to inline.

### After all workers complete (Write mode)

7. **Take Worker 3's `files` object.** For each `path → content`:
   - If file does not exist: call `Write` with the content.
   - If file exists: read it, compute the minimal edit, call `Edit`. (For new code, Write is almost always the right call.)
8. **The hooks fire here**, on the final content, exactly once per file. If a hook blocks, the orchestrator must:
   - Read the hook's stderr message.
   - Identify which worker should have caught the violation.
   - Redispatch that worker with the hook's feedback included.
   - Retry the Write.
   - If retry fails twice, surface the error to the user with the hook's diagnostic.

### After all workers complete (Review mode)

9. **Concatenate findings** from Worker 1 + Worker 2 + Worker 3.
10. **Sort by severity** (must-fix → should-fix → consider) and group by file.
11. **Present** to the user as a structured PASS/FAIL table. Cite rule codes. Do not editorialize.

### Tell the user what happened

After the pipeline completes, summarize:

```
Worker 1 (Structure):
  - Placed 2 files per ST-001 capability layout
  - Designed Order as data structure (OD-002)
  - Wired DI per DP-005 — OrderService depends on PaymentGateway interface

Worker 2 (Quality):
  - Renamed 4 placeholders to intent-revealing names (NM-001)
  - Extracted 30-line function into 3 helpers (FN-001)
  - Fixed 1 Demeter chain (OD-003)

Worker 3 (Failure):
  - Added EH-002 boundary translation around stripe.charges.create
  - Awaited 1 floating Promise (EH-004)

Files written: <list>. Hooks passed.
```

### Pipeline invariants

- **Workers never call `Write`/`Edit`.** They emit code as JSON values. Only you (the orchestrator) write to disk.
- **Hooks fire exactly once** per file, on the final code, after Worker 3.
- **No worker can modify rules outside its `owns_rules` list.** Validate before accepting output.
- **No retries past 2.** If a worker fails twice, fall back to inline.
- **Sequential, not parallel.** Worker N's output is Worker N+1's input. Do not dispatch Worker 2 before Worker 1 completes.

---

## Step 2 — Load the references

Before writing or reviewing **any** code, read these files in this order:

1. **All seven common files** (always):
   - `references/common/functions.md`
   - `references/common/naming.md`
   - `references/common/objects-and-data.md`
   - `references/common/formatting.md`
   - `references/common/error-handling.md`
   - `references/common/code-principles.md`
   - `references/common/structure.md` — the universal structural rules (folder-as-module, no deep imports, Rule of Three, no junk-drawer files). Every framework file builds on this one.

2. **The architecture file for the detected framework:**
   - `references/<framework>/structure.md`

These are short, focused documents. Read them fully — the summaries in this SKILL.md are intentionally not exhaustive. The reference files contain the worked examples, anti-patterns, and review checklists you need to apply each rule correctly.

---

## Step 3 — Apply the right rule for the right scope

The two rule sets answer different questions:

| Question | Where the answer lives |
|---|---|
| *How should this function look inside?* (size, args, side effects, names, error handling) | `common/` |
| *What should the names of files and folders be? What's the public API of this folder?* | `<framework>/structure.md` |
| *Where does a new use case go? Where does a shared helper go?* | `<framework>/structure.md` |
| *Should this class expose getters or behavior? Object or data structure?* | `common/objects-and-data.md` |
| *What goes in `shared/`? When?* | `<framework>/structure.md` (Rule of Three) |
| *SOLID, KISS, DRY?* | `common/code-principles.md` |

When the two would conflict (rare), **common rules win for the inside of code; framework rules win for the outside.** Example: `common/` says a function must be ≤ 20 lines. `nextjs/` says routes (`app/.../page.tsx`) should be thin. Both apply — the page file is short *and* its `export default function Page()` is itself short.

---

## Mode: Write vs Review

### Write mode

When you're authoring or editing code, apply the rules **proactively** — write compliant code the first time. If you catch a violation in code you just wrote, fix it before moving on. Don't ship a violation and a "TODO: fix this" comment.

### Review mode

When you're reviewing a diff, a PR, or a file, walk through the rules systematically — don't freelance.

1. **Scope.** List each file in the diff. For each, determine the framework using Step 1.
2. **Load references.** For each framework that appears in the diff, read the corresponding `<framework>/structure.md`. Always read all seven `common/` files (they apply to every file).
3. **Check each file against each applicable rule.** For each rule, either:
   - Report `PASS` (rule applies, no violations found), or
   - Report a finding as `file.tsx:42 — <which rule> — <what's wrong>`, or
   - Report `SKIPPED — <reason>` (rule does not apply to this file; explain why).
4. **Summarize.** Group findings by severity. Distinguish *must-fix* (correctness, security, broken contracts) from *should-fix* (clean-code rule, would be cleaner) from *consider* (judgement call, design tradeoff).
5. **Never silently skip a rule.** If you didn't check it, say so. A review with hidden gaps is worse than a review that admits its scope.

---

## How to find a rule when you need one

The rules are organized by **what kind of question you're asking**, not by language. Use this index:

**Functions** — size, argument count, side effects, command/query separation, exceptions vs error codes
→ `references/common/functions.md`

**Naming** — intention-revealing, no Hungarian, meaningful distinctions, pronounceable, searchable
→ `references/common/naming.md`

**Classes, objects, data structures** — getters vs behavior, Law of Demeter, hybrid classes, DTOs
→ `references/common/objects-and-data.md`

**File layout, vertical spacing, declaration placement, team conventions**
→ `references/common/formatting.md`

**Try/catch, exception design, error translation at boundaries**
→ `references/common/error-handling.md`

**SOLID, KISS, DRY, dependency inversion, single responsibility**
→ `references/common/code-principles.md`

**Folder-as-module, no deep imports, Rule of Three, no junk-drawer files (universal)**
→ `references/common/structure.md`

**Folder structure for the specific framework (Next.js routes, NestJS modules, Laravel skeleton, etc.)**
→ `references/<framework>/structure.md`

---

## On conflict — KISS wins

When two rules pull in different directions, **DP-006 (KISS)** is the tiebreaker. A simpler design that mildly bends another principle beats a complex design that satisfies them all. If you find yourself adding patterns (Strategy, Visitor, Observer, a fifth layer of indirection) to satisfy a rule, stop and ask whether the simpler version is actually wrong — usually it isn't.

---

## What this skill explicitly does NOT cover

- **Performance tuning.** Use a dedicated profiler/tool when needed. Clean code is faster *enough* by default; the rules above don't optimize hot paths.
- **Security review.** Use a dedicated security skill or auditor (e.g. the `security-review` skill, where available). A clean-code review can catch some classes of bugs (injection from string-built SQL, unvalidated input, broken authorization) but it is not a security audit.
- **Test design.** Tests are subject to the same clean-code rules (small functions, intent-revealing names) — but specific testing strategies (TDD, BDD, mutation testing) are out of scope.
- **UI/UX visual review.** That's a separate domain (typography, color, motion). The frameworks here cover *code* organization, not visual design. The `web-design-guidelines` or `design-taste-frontend` skill covers visual review when available.

If the user asks for any of the above, say so and point them at a more specific tool.

---

## Quick start for the four most common tasks

1. **"Write a component / endpoint / service."**
   Step 1 → detect framework. Step 2 → read `common/` + the framework's `structure.md`. Write the file inside the right folder, with the right name, exporting the right surface through `index.ts` (where applicable). Apply `common/functions.md` and `common/naming.md` to the code inside.

2. **"Refactor this file."**
   Read the file. Identify violations against `common/` (function too long, hidden side effect, magic number, hybrid class) and against the framework's `structure.md` (wrong folder, deep import, generic name). Apply fixes — smallest first. If a fix requires moving the file, do that explicitly and mention it.

3. **"Review this diff / PR."**
   Follow Review mode above. Don't speed-skim — most issues hide in places that look fine.

4. **"Is this clean?"**
   Read the file. Walk through `common/` rule by rule. If all pass: "yes, here's why." If any fail: list them with file:line citations and severity. Be concrete; "feels off" is not a review.

