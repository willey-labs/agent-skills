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

## Step 0 — Bootstrap the enforcement hooks (run once per skill install)

**Run this exactly once the first time the skill activates in any new session, scope, or after a skill update.** It wires the PreToolUse hooks in `hooks/` into the correct `settings.json` (project vs global is auto-detected from the SKILL.md install path).

```bash
python3 "$(dirname "$(readlink -f .claude/skills/coding-standards/SKILL.md 2>/dev/null || echo ".claude/skills/coding-standards/SKILL.md")")/bootstrap.py"
```

If that command fails to resolve (e.g. you can see this SKILL.md from another path), just call the bootstrap directly via the same dirname that this SKILL.md lives in:

```bash
python3 <skill-dir>/bootstrap.py
```

The script is **idempotent**:
- First run: creates/edits `settings.json`, adds 7 PreToolUse hook entries, prints `Wired …`.
- Re-run with no changes: prints `hooks already wired … No changes` and exits 0.
- Re-run after a skill upgrade: replaces our previous hook entry with the new one; unrelated `PreToolUse` entries are preserved.

After the first successful run the user **must restart the agent session** for the hooks to start firing. Tell the user so explicitly when bootstrap reports `Wired` or `Updated`.

If bootstrap exits with `cannot determine install scope`, the skill was invoked from somewhere outside a `.claude/skills/` tree — point the user at the install command in `README.md` and skip Step 0; the rest of the skill still applies (rules will be enforced softly via the agent reading these references, just not blocked at write time).

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

