# Activation questions — the exact payloads

The two `AskUserQuestion` payloads asked on explicit activation. SKILL.md and the `/coding-standards`
command (`commands/coding-standards.md`) both read them from here — one source, so the labels can't
drift between the two. The labels and headers are what the answer routes on: reproduce them exactly,
don't improvise your own wording.

## Mode picker

Asked on contextless activation (SKILL.md Step 2) or bare `/coding-standards` (command §2).

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

There is no Fix option — Fix mode is triggered by phrasing, never offered by the picker (SKILL.md
Step 2 has the routing).

## Run-mode question

Asked on explicit invocation, path A of SKILL.md Step 5 — after the task is known and only when the
`Agent` tool is available.

```
question:    "How should I run this?"
header:      "Run mode"
multiSelect: false
options:
  - label:       "Multiple agents (thorough)"
    description: "I spawn three specialist sub-agents in sequence — Worker 1
                  Structure → Worker 2 Code quality → Worker 3 Failure handling —
                  then write the final result. Best for a new feature, multi-file
                  work, or a full review."
  - label:       "Single agent (fast)"
    description: "I do the whole task myself in one pass. Best for a single file,
                  a small refactor, or a quick change."
```

Both questions are asked at most once per session — the answer sticks. The ask-once rules and the
routing of each answer live in SKILL.md (Steps 2 and 5), not here; this file is only the payloads.
