# block-recovery eval

The hooks only help if the agent *fixes* the code after a block instead of looping
or deleting the feature. This measures, per block message, whether a small model
given only the blocked file and the hook's stderr (no rule references) produces a
compliant fix that keeps the intent.

For each candidate fix the scorer re-runs every hook and classifies:

- **recover** — every hook passes and the intent survives (the function/class name
  is still there and the file wasn't gutted).
- **loop** — still blocked; the message didn't get the model to a fix.
- **evade** — the block clears, but the code was deleted or hollowed out.

## Run

```bash
VENV=/path/to/python-with-tree-sitter   # the TS cases need the grammars

# capture each case's real block message and build the model prompts
PYTHONPATH=. "$VENV" run_recovery.py --prompts --out-dir /tmp/rec --interpreter "$VENV"

# produce fixes: with an API key, loop prompts.json through a small model; without
# one, drive each prompt with a subagent that writes its fix to
# /tmp/rec/fixes/<case_id>__<n>.txt  (.txt — no hook scans it)

# score recover / loop / evade
PYTHONPATH=. "$VENV" run_recovery.py --score --out-dir /tmp/rec \
  --fixes-dir /tmp/rec/fixes --interpreter "$VENV"
```

The model step varies run to run; the scoring is deterministic, so a reworded
message can be regression-checked. Report a rate with its sample size, not a point
estimate.

## Files

| File | Role |
|---|---|
| `cases.py` | the block-message cases (metadata + fixture loader) |
| `fixtures.json` | the violating file bodies (JSON, so they don't trip the hooks under test) |
| `hook_probe.py` | run hooks on in-memory content; capture the block message |
| `score_fix.py` | deterministic recover / loop / evade scorer |
| `run_recovery.py` | `--prompts` / `--score` entry point |

## Scope

Content-fixable rules only: argument count, naming, `any`/`Any`, swallowed errors,
debug residue, across TS/Python/Go. Not covered: rules whose fix is a rename or a
multi-file split. A fix that changes behaviour (e.g. returning a default instead of
re-raising) still scores `recover` if it clears the block and keeps the function —
the eval measures compliant-and-intact, not best-possible. With no API key the
model is a capable small model standing in for a weaker one, so a passing score is
closer to an upper bound than a worst case.
