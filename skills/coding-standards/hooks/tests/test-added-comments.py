#!/usr/bin/env python3
"""Regression test — CM-007, the one-line limit on comment blocks a write adds.

Checks that a multi-line block mid-file is refused, that a real file-header docstring
and stacked machine pragmas are not, and that prose already on disk is never
re-judged. The disk cases run against a real file.

    python3 hooks/tests/test-added-comments.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, report_failures, run_cases  # noqa: E402

HOOK = "block-added-comments.py"
HOOKS_DIR = Path(__file__).resolve().parent.parent

EXISTING_BLOCK = (
    "const RETRY = 3;\n"
    "\n"
    "/** A fourth retry outlasts the caller's deadline. A higher cap was tempting\n"
    " *  given how often the sandbox flakes, but the gateway holds the connection\n"
    " *  open for the whole window, so the extra attempt buys nothing at all and\n"
    " *  costs the caller its own timeout budget. */\n"
    "export const cap = RETRY;\n"
)

CASES = [
    Case(
        "one-line rationale passes",
        HOOK,
        "/tmp/cs/src/a.ts",
        "const a = 1;\n\n// A 4th retry outlasts the caller's deadline (FIN-2231).\nconst b = a;\n",
        block=False,
    ),
    Case(
        "two-line block is refused",
        HOOK,
        "/tmp/cs/src/b.ts",
        "const a = 1;\n\n// Rounds half-up so the figure matches\n// the invoice PDF finance generates.\nconst b = a;\n",
        block=True,
        rule="CM-007",
    ),
    Case(
        "four-line JSDoc is refused",
        HOOK,
        "/tmp/cs/src/c.ts",
        "const a = 1;\n\n/**\n * Formats the amount for the invoice header,\n * rounding half-up so it matches the PDF\n * the finance team generates.\n */\nexport function fmt(n: number) {\n  return n;\n}\n",
        block=True,
        rule="CM-007",
    ),
    Case(
        "three-line python block is refused",
        HOOK,
        "/tmp/cs/src/d.py",
        'x = 1\n\n\ndef f():\n    # The bulk endpoint drops ordering, so we send\n    # one row per request and reassemble client side\n    # once every response has landed.\n    return x\n',
        block=True,
        rule="CM-007",
    ),
    Case(
        "file-header docstring is exempt",
        HOOK,
        "/tmp/cs/src/e.py",
        '#!/usr/bin/env python3\n"""What this module does.\n\nA second paragraph, and a third line, and a fourth, all of which describe\nthe unit rather than any one line of it.\n"""\n\n\ndef f():\n    return 1\n',
        block=False,
    ),
    Case(
        "stacked eslint pragmas are exempt",
        HOOK,
        "/tmp/cs/src/f.ts",
        "const a = 1;\n\n/* eslint-disable no-console */\n/* eslint-disable no-shadow */\nconsole.log(a);\n",
        block=False,
    ),
    Case(
        "stacked python pragmas are exempt",
        HOOK,
        "/tmp/cs/src/g.py",
        "x = 1\n\n\ndef f():\n    # type: ignore[arg-type]\n    # pylint: disable=broad-except\n    # noqa: E402\n    return x\n",
        block=False,
    ),
    Case(
        "a block opening a function body is refused",
        HOOK,
        "/tmp/cs/src/j.py",
        "def total(values):\n    # Sums the values and returns the result.\n    # A manual loop was tempting but sum() reads better at this size.\n    return sum(values)\n",
        block=True,
        rule="CM-007",
    ),
    Case(
        "an encoding line before the header block is exempt",
        HOOK,
        "/tmp/cs/src/k.py",
        '# -*- coding: utf-8 -*-\n"""What this module does.\n\nA second line and a third, describing the unit rather than any one line of it.\n"""\n\n\ndef f():\n    return 1\n',
        block=False,
    ),
    Case(
        "a block under the module docstring is refused",
        HOOK,
        "/tmp/cs/src/l.py",
        '"""What this module does."""\n\n# Rounds half-up so the figure matches\n# the invoice the finance team generates.\nRATE = 1\n',
        block=True,
        rule="CM-007",
    ),
    Case(
        "a file with no comments passes",
        HOOK,
        "/tmp/cs/src/h.ts",
        "const total = items.reduce((sum, i) => sum + i.price, 0);\nexport { total };\n",
        block=False,
    ),
    Case(
        "excluded path is skipped",
        HOOK,
        "/tmp/cs/node_modules/pkg/i.ts",
        "const a = 1;\n\n// Rounds half-up so the figure matches\n// the invoice PDF finance generates.\nconst b = a;\n",
        block=False,
    ),
]


def run_against_disk(content_on_disk: str, written: str) -> int:
    """Exit code for a Write of `written` to a file already holding `content_on_disk`."""
    with tempfile.TemporaryDirectory() as workdir:
        target = Path(workdir) / "toast.ts"
        target.write_text(content_on_disk, encoding="utf-8")
        payload = json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": str(target), "content": written}}
        )
        proc = subprocess.run(
            [sys.executable, str(HOOKS_DIR / HOOK)],
            input=payload,
            capture_output=True,
            text=True,
        )
        return proc.returncode


def disk_failures() -> list[str]:
    """The two cases that need the prior content to exist on disk."""
    failures: list[str] = []
    kept = run_against_disk(EXISTING_BLOCK, EXISTING_BLOCK.replace("RETRY = 3", "RETRY = 4"))
    if kept == 2:
        failures.append("existing block re-judged: editing code near old prose must pass")
    added = run_against_disk(
        EXISTING_BLOCK,
        EXISTING_BLOCK + "\n// Pinned to light because the design system\n// authors no dark surfaces.\nexport const theme = 'light';\n",
    )
    if added != 2:
        failures.append(f"new block alongside an existing one must be refused, got exit {added}")
    return failures


if __name__ == "__main__":
    sys.exit(
        report_failures(
            "added-comment (CM-007)",
            run_cases(CASES) + disk_failures(),
            len(CASES) + 2,
        )
    )
