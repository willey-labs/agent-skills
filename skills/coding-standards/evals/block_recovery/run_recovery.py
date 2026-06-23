#!/usr/bin/env python3
"""recovery eval — one entry point.

Measures, per block message, whether a small model given only the blocked file and
the hook's stderr (no rule references) produces a compliant fix that keeps intent.

Two phases, because the model can't be called from inside the script without an
API key:

  1. `--prompts`  capture each case's block message and write `prompts.json` (file
                  + stderr + the prompt to hand a model). With a key, loop these
                  through a model; without one, drive each with a subagent that
                  writes its fix to `<fixes-dir>/<case_id>__<n>.txt`.
  2. `--score`    read the fixes, score recover / loop / evade (deterministic —
                  re-runs the hooks), and write `recovery-report.json`.

The model step varies; the scoring is deterministic, so a reworded message can be
regression-checked. Report a rate with its sample size.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from cases import CASES, load_fixtures
from hook_probe import block_message
from score_fix import score

_PROMPT = """\
A code-quality tool blocked you from saving this file. Below is the file you wrote \
and the tool's error message.

Rewrite the file so the tool no longer blocks it, while keeping exactly what the \
code does. Do NOT delete the function or class and do NOT remove the feature to \
make the error go away — fix it properly. Return ONLY the full corrected file \
contents, with no explanation and no markdown fences.

----- FILE: {file_name} -----
{original}

----- TOOL ERROR -----
{block}
"""


@dataclass(frozen=True)
class RecoveryArgs:
    mode: str
    out_dir: Path
    fixes_dir: Path
    interpreter: str


def _parse_args(argv: list[str]) -> RecoveryArgs:
    parser = argparse.ArgumentParser(description="block-recovery eval")
    parser.add_argument("--prompts", action="store_true")
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--fixes-dir", default="")
    parser.add_argument("--interpreter", required=True)
    ns = parser.parse_args(argv)
    return RecoveryArgs(
        mode="score" if ns.score else "prompts",
        out_dir=Path(ns.out_dir),
        fixes_dir=Path(ns.fixes_dir) if ns.fixes_dir else Path(ns.out_dir) / "fixes",
        interpreter=ns.interpreter,
    )


def _write_prompts(interpreter: str, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    fixtures = load_fixtures()
    records = []
    for case in CASES:
        original = fixtures[case.case_id]
        block = block_message(interpreter, case.file_name, original)
        if not block:
            print(f"WARNING: {case.case_id} did not block — drop or fix the fixture")
            continue
        records.append(
            {
                "case_id": case.case_id,
                "rule": case.rule,
                "file_name": case.file_name,
                "block_message": block,
                "original": original,
                "prompt": _PROMPT.format(file_name=case.file_name, original=original, block=block),
            }
        )
    (out_dir / "prompts.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"wrote {len(records)} prompts -> {out_dir / 'prompts.json'}")
    return 0


def _read_fixes(fixes_dir: Path) -> dict[str, list[str]]:
    fixes: dict[str, list[str]] = {}
    for path in sorted(fixes_dir.glob("*.txt")):
        case_id = path.name.split("__", 1)[0]
        fixes.setdefault(case_id, []).append(path.read_text(encoding="utf-8"))
    return fixes


def _aggregate(fixes: dict[str, list[str]], interpreter: str) -> list[dict[str, object]]:
    fixtures = load_fixtures()
    case_by_id = {c.case_id: c for c in CASES}
    rows: list[dict[str, object]] = []
    for case in CASES:
        candidates = fixes.get(case.case_id, [])
        counts: Counter[str] = Counter()
        reasons: list[str] = []
        for fixed in candidates:
            verdict = score(case, fixtures[case.case_id], fixed, interpreter)
            counts[verdict.outcome] += 1
            reasons.append(f"{verdict.outcome}: {verdict.reason}")
        rows.append(
            {
                "case_id": case.case_id,
                "rule": case.rule,
                "n": len(candidates),
                "recover": counts["recover"],
                "loop": counts["loop"],
                "evade": counts["evade"],
                "detail": reasons,
            }
        )
    return rows


def _print_report(rows: list[dict[str, object]]) -> None:
    print("=== recovery (per block message) ===\n")
    print(f"{'case':12s} {'rule':8s} {'n':>3s} {'recover':>8s} {'loop':>5s} {'evade':>6s}")
    totals: Counter[str] = Counter()
    for row in rows:
        print(
            f"{row['case_id']:12s} {row['rule']:8s} {row['n']:3d} "
            f"{row['recover']:8d} {row['loop']:5d} {row['evade']:6d}"
        )
        for key in ("recover", "loop", "evade", "n"):
            totals[key] += int(row[key])
    n = totals["n"] or 1
    print(f"\noverall: n={totals['n']}  recover={totals['recover']} ({totals['recover'] / n:.0%})  "
          f"loop={totals['loop']} ({totals['loop'] / n:.0%})  evade={totals['evade']} ({totals['evade'] / n:.0%})")
    weak = [r for r in rows if r["n"] and r["recover"] < r["n"]]
    if weak:
        print("\nmessages that did not recover every sample (candidates for rewording):")
        for row in weak:
            print(f"  - {row['case_id']} ({row['rule']}): {row['detail']}")


def _run_score(args: RecoveryArgs) -> int:
    fixes = _read_fixes(args.fixes_dir)
    if not fixes:
        print(f"no fixes in {args.fixes_dir} — generate them from prompts.json first")
        return 1
    rows = _aggregate(fixes, args.interpreter)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "recovery-report.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _print_report(rows)
    return 0


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if args.mode == "score":
        return _run_score(args)
    return _write_prompts(args.interpreter, args.out_dir)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
