#!/usr/bin/env python3
"""false-block-rate eval — one entry point.

Two phases, because classification is a judgement the runner can't make:

  1. `--scan`   clone the pinned corpus, run every hook over every (capped) source
                file, write `blocks.json` and `scan-summary.json`. Prints what was
                sampled and which frameworks have no corpus entry.
  2. `--report` read `blocks-classified.json` (blocks.json + a verdict per hard
                block, from classify.py) and print the per-hook and overall rate.

Re-running `--scan` reuses existing clones, so the measurement is repeatable
against the pinned SHAs.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from clone_corpus import clone_all
from compute_rate import print_rate_report
from corpus import CORPUS, UNCOVERED_FRAMEWORKS
from scan_corpus import RepoScan, ScanContext, scan_repo

_DEFAULT_MAX_FILES = 150


@dataclass(frozen=True)
class EvalArgs:
    mode: str
    cache_dir: Path
    out_dir: Path
    interpreter: str
    max_files: int


def _parse_args(argv: list[str]) -> EvalArgs:
    parser = argparse.ArgumentParser(description="false-block-rate eval")
    parser.add_argument("--scan", action="store_true", help="clone + scan the corpus")
    parser.add_argument("--report", action="store_true", help="print the rate from classified blocks")
    parser.add_argument("--cache-dir", required=True, help="where corpus clones live")
    parser.add_argument("--out-dir", required=True, help="where blocks.json / summary are written")
    parser.add_argument("--interpreter", required=True, help="python that can import tree-sitter")
    parser.add_argument("--max-files", type=int, default=_DEFAULT_MAX_FILES)
    ns = parser.parse_args(argv)
    return EvalArgs(
        mode="report" if ns.report else "scan",
        cache_dir=Path(ns.cache_dir),
        out_dir=Path(ns.out_dir),
        interpreter=ns.interpreter,
        max_files=ns.max_files,
    )


def _print_sampling(scans: list[RepoScan], max_files: int) -> None:
    print(f"Sampled corpus (max {max_files} files/repo, deterministic sort):")
    for scan in scans:
        capped = " [CAPPED]" if scan.files_scanned < scan.files_total else ""
        hard = sum(1 for b in scan.blocks if not b.is_advisory)
        print(
            f"  {scan.name:30s} {scan.framework:12s} "
            f"{scan.files_scanned}/{scan.files_total} files  {hard} hard blocks{capped}"
        )
    print("\nFrameworks with NO corpus entry (rate does NOT cover these):")
    for fw in UNCOVERED_FRAMEWORKS:
        print(f"  - {fw}")


def _write_blocks(scans: list[RepoScan], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = [asdict(b) for scan in scans for b in scan.blocks]
    (out_dir / "blocks.json").write_text(json.dumps(blocks, indent=2), encoding="utf-8")
    summary = [
        {
            "name": s.name,
            "framework": s.framework,
            "files_total": s.files_total,
            "files_scanned": s.files_scanned,
        }
        for s in scans
    ]
    (out_dir / "scan-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _run_scan(args: EvalArgs) -> int:
    checkouts = clone_all(args.cache_dir)
    context = ScanContext(interpreter=args.interpreter, hook_dir=_hook_dir(), max_files=args.max_files)
    scans = [scan_repo(context, spec, checkouts[spec.name]) for spec in CORPUS]
    _write_blocks(scans, args.out_dir)
    _print_sampling(scans, args.max_files)
    print(f"\nWrote {args.out_dir / 'blocks.json'} — classify hard blocks into blocks-classified.json")
    return 0


def _hook_dir() -> Path:
    # evals/false_block_rate/run_eval.py -> skills/coding-standards/hooks
    return Path(__file__).resolve().parents[2] / "hooks"


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if args.mode == "report":
        return print_rate_report(args.out_dir / "blocks-classified.json")
    return _run_scan(args)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
