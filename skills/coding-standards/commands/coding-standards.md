---
description: Apply the coding-standards skill. Bare invocation opens a guided picker; pass a task description to skip the picker.
argument-hint: "[task description — e.g. 'review this PR', 'write a checkout form', 'show me the naming rules']"
---

The user invoked `/coding-standards` with arguments: `$ARGUMENTS`

You are now using the **coding-standards** skill. The skill lives at `~/.claude/skills/coding-standards/` (global install) or `<project>/.claude/skills/coding-standards/` (project install).

## Routing logic

### Always first — Step 0 (bootstrap)

Run `python3 <skill-dir>/bootstrap.py` exactly once per session if you haven't already. The script is idempotent and self-detects scope. If it reports `Wired` or `Updated`, tell the user to restart the agent session so hooks activate.

### Then route by `$ARGUMENTS`

**If `$ARGUMENTS` is empty** (the user typed just `/coding-standards`):
→ Invoke the `AskUserQuestion` tool with the exact payload below. Do not proceed until the user picks one.

```
question:    "What do you want to do with the coding-standards skill?"
header:      "Mode"
multiSelect: false
options:
  - label:       "Write code that follows these rules"
    description: "I'll detect the framework (Next.js, NestJS, Django, Laravel,
                  Spring Boot, Go HTTP, etc.) from your project, load the matching
                  references, and apply the rules as I write. Hard violations
                  (banned types, Hungarian, 4+ args, junk-drawer paths) get blocked
                  at write time by the installed hooks."

  - label:       "Check existing code against these rules"
    description: "Point me at a file, folder, or diff and I'll report violations.
                  For each file I list PASS / FAIL / SKIPPED per applicable rule
                  with file:line citations, grouped by must-fix / should-fix /
                  consider. See references/<framework>/structure.md anti-patterns
                  for the strict review checklist."

  - label:       "Show me the rules"
    description: "Guided tour of the 7 universal rule families (FN-* functions,
                  NM-* naming, OD-* objects & data, ST-* structure, EH-* errors,
                  FMT-* formatting, DP-* code principles) plus the framework I
                  detect for your project. I'll cite rule codes with worked
                  examples from references/common/ and references/<framework>/."
```

After the user picks:
- **Write code…** → Step 1 (framework detection) → **Step 1.4 (resolve structure — ask the structure question first if custom)** → Step 1.5 (orchestrator pipeline because `/coding-standards` was used explicitly — pipeline is the default for this command) → Step 2.O (workers).
- **Check existing code…** → ask the user *what* to check (file path, folder, diff command, or PR number) → Step 1 (per-file framework detection) → **Step 1.4 (resolve structure — ask the structure question first if custom)** → Step 1.5 (orchestrator pipeline) → Step 2.O (workers in review mode).
- **Show me the rules** → Step 1 (detect framework once) → Step 1.4 (resolve structure silently — no question) → Step 2 (load all refs inline; no workers) → present a one-screen index of rule codes, then wait for follow-up questions.

**If `$ARGUMENTS` is non-empty** (the user typed `/coding-standards <something>`):
→ Treat `$ARGUMENTS` as the task. Skip the picker entirely. Examples:

| `$ARGUMENTS` | Mode |
|---|---|
| `write a checkout form` | Write |
| `review this PR` / `audit this file` / `check this diff` | Review |
| `is this clean?` (with a target) | Review |
| `show me the naming rules` / `what's FN-005?` | Show me the rules / Q&A |
| `refactor src/cart.ts` | Write (targeted at the path) |

Apply Step 1 (framework detect) → **Step 1.4 (resolve structure — ask the structure question first if custom)** → Step 1.5 (orchestrator pipeline default when `/coding-standards` was invoked) → Step 2.O (workers) → integration → final Write.

**Resolve structure (Step 1.4) before the run-mode question** — the structure question is always the first interactive prompt; run-mode is second.

**Because `/coding-standards` was used explicitly, ask the user how to run it** (SKILL.md Step 1.5, path A): once the task is known, invoke `AskUserQuestion` with the "Run mode" question — **Multiple agents** (you, the main agent, dispatch Worker 1 → Worker 2 → Worker 3 via the `Agent` tool — i.e. the Step 2.O orchestrator) vs **Single agent** (you do it inline). Run whichever the user picks and announce it. Skip the question and go inline (saying so) only when the `Agent` tool isn't available in this host, or for the "Show me the rules" mode. Ask the run-mode question at most once per session.

## Do not

- Do not invoke `AskUserQuestion` if `$ARGUMENTS` already names a task.
- Do not invoke `AskUserQuestion` more than once per session — once mode is chosen, it stays chosen until the user says otherwise.
- Reproduce the option **labels** and the **header** ("Mode") verbatim — they are the routing contract shared with `SKILL.md` Step 0.5 (the agent matches the user's answer against the label text). The descriptions below are the richer `/coding-standards` variant; keep them faithful to the SKILL.md meaning, but they need not be byte-identical to SKILL.md's shorter descriptions.
