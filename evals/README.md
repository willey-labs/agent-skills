# Evals

Measures whether the `coding-standards` skill changes what an agent writes. Every case runs the same prompt twice per run, once with the skill and once without, and scores both with the same graders. The report gives each case's score in both arms and the difference.

Eval runs load the skill's instructions but not its write-time hooks, which the installer wires into `settings.json`. The suite therefore measures what the instructions alone change; with the hooks installed, a violating write is refused on top of that.

A case is a directory holding `prompt.md` (the request plus run settings) and `graders/`. Graders are regex checks on the files the agent wrote, file-existence checks, tool-call checks, and rubric checks a separate model votes on three times.

## Cases

| Kind | Cases | What they check |
|---|---|---|
| Write | new code from a spec, in TypeScript, Python, Go, C#, Java, Kotlin and PHP, across the frameworks the skill covers | the task is solved correctly, and the code follows the rules: no `any`/`Any`/`dynamic`/`mixed`, no swallowed errors, no wide signatures, no multi-line comment blocks, no junk-drawer files, readable design |
| Refactor | pasted code with Hungarian names, `any`, swallowed errors and narrating comments, plus a feature to add | the saved file is a new file, so it is held to the rules: added code is clean, and the pasted swallowed errors, debug output and narrating comments are gone |
| Fix | pasted code with a bug | the bug is fixed |
| Review | pasted code with known defects | the reply names the real defects and doesn't invent others |
| Negative | requests that involve no code | the skill does not fire |

Tags in each `prompt.md` (`python`, `write`, `fastapi`, `negative`, …) select subsets with `--tag`.

## Run

From the repo root:

```bash
claude plugin eval . --no-publish --allow-tools Write Edit -j 4
claude plugin eval . --no-publish --allow-tools Write Edit --tag python
claude plugin eval . --no-publish --allow-tools Write Edit --case '03-*' --runs 5
```

`--allow-tools Write Edit` is required: without it the agent cannot create files and every code case fails in both arms. Results land in `evals/results/`, which is git-ignored. `--model` repeats the suite on another model.
