#!/usr/bin/env python3
"""Regression cases for `check-review-report.py`.

The validator is a CLI over a report file (not a Write-payload hook), so it gets
its own driver instead of the shared `harness.py`. Each case builds a temp repo
with a review report and asserts the exit code: 0 grounded, 1 declared skip,
2 inconsistent/missing.

Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "check-review-report.py"

GROUNDED = 0
DECLARED_SKIP = 1
INCONSISTENT = 2


def _report_body(baseline_line: str) -> str:
    return (
        "# Coding-standards review — 2026-06-23-120000\n\n"
        "- **Scope:** src/feature/widget.ts\n"
        "- **Framework:** nextjs\n"
        f"{baseline_line}\n"
        "- **Run mode:** inline\n\n"
        "## Findings\n| ID | File:Line | Rule | Issue | Fix |\n|---|---|---|---|---|\n"
        "| F001 | a:1 | FN-001 | x | y |\n"
    )


@dataclass(frozen=True)
class Case:
    name: str
    baseline_line: str
    structure_at: str | None  # relative path to create a structure file, or None
    expected: int


CASES = [
    Case(
        "grounded — file present at root",
        "- **Structure baseline:** follows feature-first — recorded at `.coding-standards-structure`",
        ".coding-standards-structure",
        GROUNDED,
    ),
    Case(
        "grounded — monorepo sub-project path",
        "- **Structure baseline:** custom — recorded at `apps/web/.coding-standards-structure`",
        "apps/web/.coding-standards-structure",
        GROUNDED,
    ),
    Case(
        "inconsistent — claims a structure but no file (the silent-skip bug)",
        "- **Structure baseline:** follows feature-first — recorded at `.coding-standards-structure`",
        None,
        INCONSISTENT,
    ),
    Case(
        "declared skip — NOT RECORDED with a reason",
        "- **Structure baseline:** NOT RECORDED — structural review not grounded (unsupported framework: SvelteKit)",
        None,
        DECLARED_SKIP,
    ),
    Case(
        "missing — no baseline field at all",
        "- **Notes:** none",
        None,
        INCONSISTENT,
    ),
]


def run_case(case: Case) -> str | None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        reviews = root / ".coding-standards" / "reviews"
        reviews.mkdir(parents=True)
        report = reviews / "2026-06-23-120000.md"
        report.write_text(_report_body(case.baseline_line), encoding="utf-8")

        if case.structure_at is not None:
            target = root / case.structure_at
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("follows: feature-first\n", encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(report)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != case.expected:
            output = (proc.stdout + proc.stderr).strip()
            return f"{case.name}: expected exit {case.expected}, got {proc.returncode}: {output}"
    return None


def main() -> int:
    failures = [msg for msg in (run_case(c) for c in CASES) if msg is not None]
    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    print(f"ok — {len(CASES)} review-report-check cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
