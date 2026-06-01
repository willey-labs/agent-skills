---
description: Apply the coding-standards skill. Bare invocation opens a guided picker; pass a task description to skip the picker.
argument-hint: "[task description — e.g. 'review this PR', 'write a checkout form', 'show me the naming rules']"
---

The user invoked `/coding-standards` with arguments: `$ARGUMENTS`

This activates the **coding-standards** skill — follow `SKILL.md` for the full flow (framework detection,
structure resolution, reference loading, the pipeline). This command only adds three things on top:
bootstrap, `$ARGUMENTS` routing, and the explicit-invocation run-mode default.

## 1. Bootstrap first (Step 0)

Run the read-only check once per session (single absolute-path command, no `cd`/operators, so it matches
the pre-approved permission rule):

```bash
python3 <skill-dir>/bootstrap.py --verify
```

Exit 0 → already wired; go to routing. Non-zero → run `python3 <skill-dir>/bootstrap.py --auto-install`,
then act on its result (`Wired` / `Updated` → ask the user to restart the session; `Blocking issues:` →
surface verbatim and stop). Detail lives in SKILL.md Step 0 and `references/bootstrap.md`.

## 2. Route by `$ARGUMENTS`

**Empty** (`/coding-standards` alone) → invoke `AskUserQuestion` with this exact payload and wait. The
**labels and header are the routing contract** — reproduce them verbatim (shared with SKILL.md Step 0.5);
the descriptions may differ.

```
question:    "What do you want to do with the coding-standards skill?"
header:      "Mode"
multiSelect: false
options:
  - label:       "Write code that follows these rules"
    description: "Detect the framework, load the matching references, and apply the
                  rules as I write. Hard violations are blocked at write time."
  - label:       "Check existing code against these rules"
    description: "Point me at a file, folder, or diff; I report PASS / FAIL / SKIPPED
                  per rule with file:line citations, grouped by severity."
  - label:       "Show me the rules"
    description: "A guided tour of the rule families plus the framework I detect for
                  your project, with worked examples."
```

**Non-empty** → treat `$ARGUMENTS` as the task and skip the picker:

| `$ARGUMENTS` | Mode |
|---|---|
| `write a checkout form`, `refactor src/cart.ts` | Write |
| `review this PR`, `audit this file`, `check this diff`, `is this clean?` (with a target) | Review |
| `show me the naming rules`, `what's FN-005?` | Show me the rules / Q&A |

Either way, hand off to SKILL.md from Step 1 (framework detection) onward.

## 3. Explicit-invocation default: ask the run-mode question

Because `/coding-standards` was invoked explicitly, use SKILL.md Step 1.5 **path A**: once the task is
known (and it's Write or Review, not Q&A), ask the "Run mode" question (Multiple agents vs Single agent)
and run the user's choice. Structure resolution (Step 1.4) still comes first; run-mode is the second
question. Skip the run-mode question only when the `Agent` tool is unavailable in this host — then go
inline and say so.

## Do not

- Don't invoke `AskUserQuestion` if `$ARGUMENTS` already names a task.
- Don't invoke it more than once per session — once mode is chosen, it stays chosen unless the user says otherwise.
