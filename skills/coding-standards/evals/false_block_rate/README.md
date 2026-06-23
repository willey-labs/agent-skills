# false-block-rate eval

Measures how often the hooks hard-block real, idiomatic open-source code. The
hooks are a binary hard block aimed at users who can't tell a false positive from
a real one, so the rate at which they stop clean code is the number that decides
whether the skill is safe to ship.

A block falls into one of three buckets:

- **true positive** — a real violation a reviewer would fix.
- **misfire** — the regex/AST matched something that isn't an instance of the
  pattern (a bug). This is the rate to keep under ~1%.
- **stance block** — the match is correct, but the code is idiomatic and only
  blocks because a rule takes a deliberate position against the pattern (e.g. Go
  `any`). This is what predicts day-to-day friction.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install tree_sitter tree_sitter_typescript tree_sitter_javascript
VENV=$(pwd)/.venv/bin/python

# clone the pinned corpus and run every hook over every source file
PYTHONPATH=. "$VENV" run_eval.py --scan \
  --cache-dir /tmp/corpus --out-dir /tmp/results --interpreter "$VENV" --max-files 150

# record the verdict on each hard block, then print the rate
PYTHONPATH=. python3 classify.py /tmp/results/blocks.json /tmp/results/blocks-classified.json
PYTHONPATH=. python3 compute_rate.py /tmp/results/blocks-classified.json
```

Repos are pinned to commit SHAs in `corpus.py`, so the measurement is repeatable.
A `--scan` reuses existing clones. After a hook change, re-run all three; any
unseen (repo, rule) cluster is flagged `unclassified` rather than scored silently.

## Files

| File | Role |
|---|---|
| `corpus.py` | pinned repos, per-repo extensions, dir/test-file skips |
| `clone_corpus.py` | depth-1 fetch of each pinned commit |
| `scan_corpus.py` | run each hook per file, attribute every block to its hook |
| `classify.py` | the recorded verdict per (repo, rule) cluster |
| `compute_rate.py` | per-hook and overall rate |
| `run_eval.py` | `--scan` / `--report` entry point |

## Notes

The corpus is official templates and widely-used frameworks — clean, idiomatic
code, which biases the number toward stance blocks over true positives. Pick is in
`corpus.py`. `django` is capped by `--max-files`; the cap is printed, never
silent. Frameworks with no corpus entry are listed in `corpus.py` so the rate is
never mistaken for full coverage. Classification is judgement, recorded in
`classify.py` so it can be argued with and re-run.
