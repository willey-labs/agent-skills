#!/usr/bin/env python3
"""Compute the false-block rate from classified hard blocks.

Reads `blocks-classified.json` — each hard block with a `verdict` ("tp" for a real
violation) and, for false positives, an `fp_kind`:

  - "misfire" — the regex/AST matched something that isn't an instance of the
    pattern (a bug). Keep this rate under ~1%.
  - "stance"  — the match is correct, but it blocks idiomatic code on a deliberate
    rule position.

Advisories (exit 0 + stderr) are excluded; they never stop a write. Reports the
misfire rate per hook and the share of scanned files blocked on idiomatic code.

Stdlib only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_BAR = 0.01  # a hard-block pattern over ~1% misfire rate doesn't belong


@dataclass
class HookTally:
    hook: str
    hard: int = 0
    misfire: int = 0
    stance: int = 0
    fp_examples: list[str] = field(default_factory=list)

    @property
    def misfire_rate(self) -> float:
        return self.misfire / self.hard if self.hard else 0.0

    @property
    def block_rate(self) -> float:
        return (self.misfire + self.stance) / self.hard if self.hard else 0.0


def _load_blocks(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [b for b in data if isinstance(b, dict) and not b.get("is_advisory")]


def _load_files_scanned(report_dir: Path) -> int:
    summary_path = report_dir / "scan-summary.json"
    if not summary_path.is_file():
        return 0
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return sum(int(row.get("files_scanned", 0)) for row in summary if isinstance(row, dict))


def _tally_by_hook(blocks: list[dict[str, object]]) -> dict[str, HookTally]:
    tallies: dict[str, HookTally] = {}
    for block in blocks:
        hook = str(block.get("hook", "?"))
        tally = tallies.setdefault(hook, HookTally(hook=hook))
        tally.hard += 1
        kind = block.get("fp_kind")
        if kind == "misfire":
            tally.misfire += 1
        elif kind == "stance":
            tally.stance += 1
        if block.get("verdict") == "fp":
            tally.fp_examples.append(f"{block.get('repo')}:{block.get('file')} — {block.get('verdict_reason')}")
    return tallies


def _count_unclassified(blocks: list[dict[str, object]]) -> int:
    return sum(1 for b in blocks if b.get("verdict") == "unclassified")


def _print_hook_table(tallies: dict[str, HookTally]) -> None:
    print(f"{'hook':30s} {'blocks':>6s} {'misfire':>8s} {'stance':>7s} {'mf-rate':>8s}")
    for hook in sorted(tallies):
        t = tallies[hook]
        flag = "  <-- OVER 1% BAR" if t.misfire_rate > _BAR else ""
        print(f"{hook:30s} {t.hard:6d} {t.misfire:8d} {t.stance:7d} {t.misfire_rate:7.1%}{flag}")


def _print_overall(tallies: dict[str, HookTally], blocks: list[dict[str, object]], files: int) -> None:
    hard = sum(t.hard for t in tallies.values())
    misfire = sum(t.misfire for t in tallies.values())
    stance = sum(t.stance for t in tallies.values())
    fp_files = {f"{b.get('repo')}:{b.get('file')}" for b in blocks if b.get("verdict") == "fp"}
    print("\n--- overall ---")
    print(f"files scanned                 : {files}")
    print(f"hard blocks                   : {hard}")
    print(f"regex/AST misfires            : {misfire}  ({misfire / hard:.2%} of blocks)" if hard else "")
    print(f"stance blocks (idiomatic)     : {stance}  ({stance / hard:.1%} of blocks)" if hard else "")
    if files:
        print(f"files blocked on idiomatic code: {len(fp_files)}  ({len(fp_files) / files:.1%} of files scanned)")
    unresolved = _count_unclassified(blocks)
    if unresolved:
        print(f"\nWARNING: {unresolved} hard blocks unclassified — rate is incomplete.")


def _print_idiomatic_drivers(tallies: dict[str, HookTally]) -> None:
    print("\n--- what drives the idiomatic-code blocks (stance + any misfire) ---")
    for hook in sorted(tallies, key=lambda h: -(tallies[h].misfire + tallies[h].stance)):
        t = tallies[hook]
        if not t.fp_examples:
            continue
        print(f"\n{hook}  ({t.misfire + t.stance} fp; block-rate {t.block_rate:.0%}):")
        seen: set[str] = set()
        for ex in t.fp_examples:
            reason = ex.split(" — ", 1)[-1]
            if reason in seen:
                continue
            seen.add(reason)
            print(f"  - {ex}")


def print_rate_report(classified_path: Path) -> int:
    if not classified_path.is_file():
        print(f"missing {classified_path} — run --scan, classify.py, then --report")
        return 1
    blocks = _load_blocks(classified_path)
    tallies = _tally_by_hook(blocks)
    files = _load_files_scanned(classified_path.parent)
    print("=== false-block rate ===\n")
    _print_hook_table(tallies)
    _print_overall(tallies, blocks, files)
    _print_idiomatic_drivers(tallies)
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: compute_rate.py <blocks-classified.json>")
        sys.exit(1)
    sys.exit(print_rate_report(Path(sys.argv[1])))
