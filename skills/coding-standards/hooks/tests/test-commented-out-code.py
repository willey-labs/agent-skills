#!/usr/bin/env python3
"""Regression test — FMT-005 commented-out-code advisory, precision and recall.

The check runs on raw lines because it has to read comment text, which puts it one
step from ordinary English. The cases below pin both directions: a disabled call or
assignment is still caught, and a comment whose prose merely contains a parenthetical
is not — that shape ("names it (and replaces it) on re-run") is everywhere in real
comments, so treating it as code would make the advisory noise.

The advisory never blocks, so the assertion is on the message, not the exit code.

    python3 hooks/tests/test-commented-out-code.py
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(TESTS_DIR.parent))

from harness import report_failures, run_hook  # noqa: E402

HOOK = "block-debug-artifacts.py"

FLAGGED = [
    ("disabled call", "// sendEmail(user);\nexport const x = 1\n"),
    ("disabled assignment", "// total = total + 1\nexport const x = 1\n"),
    ("disabled spaced assignment", "// total = 0\nexport const x = 1\n"),
    ("disabled declaration", "// const cached = load();\nexport const x = 1\n"),
    ("disabled block tail", "// }\nexport const x = 1\n"),
]

CLEAN = [
    ("prose parenthetical", "// It names the entry (and replaces it) on a re-run.\nexport const x = 1\n"),
    ("prose parenthetical mid-sentence", "// Retries twice (the gateway drops the first call).\nexport const x = 1\n"),
    ("plain prose", "// The gateway rounds half-to-even; invoices round half-up.\nexport const x = 1\n"),
]


def check(name: str, content: str, expect_finding: bool) -> str | None:
    code, stderr = run_hook(HOOK, "/tmp/fmt005/src/a.ts", content)
    if code != 0:
        return f"{name}: advisory must exit 0, got {code}"
    flagged = "commented-out code" in stderr
    if flagged != expect_finding:
        want = "a finding" if expect_finding else "silence"
        return f"{name}: expected {want}, got {stderr.strip() or '<silence>'}"
    return None


def main() -> int:
    failures = [
        result
        for result in (
            [check(name, content, True) for name, content in FLAGGED]
            + [check(name, content, False) for name, content in CLEAN]
        )
        if result
    ]
    return report_failures("commented-out-code", failures, len(FLAGGED) + len(CLEAN))


if __name__ == "__main__":
    sys.exit(main())
