#!/usr/bin/env python3
"""Regression test — FMT-005 print residue is skipped where printing is the program's output.

A program entry point (shebang, `__main__` guard, `main` function) prints by design,
so print-style calls there draw no advisory. The same call in a library file still
does, and the hard-blocked debugger forms stay blocked in an entry point.

    python3 hooks/tests/test-print-in-entry-points.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import report_failures, run_hook  # noqa: E402

HOOK = "block-debug-artifacts.py"


@dataclass
class PrintCase:
    """Whether a write draws the FMT-005 print advisory, and the exit code it must return."""

    name: str
    file_path: str
    content: str
    advised: bool
    exit_code: int = 0


CASES = [
    PrintCase(
        "python __main__ script prints",
        "/tmp/fmt/tools/report.py",
        'def main():\n    print("done")\n\n\nif __name__ == "__main__":\n    main()\n',
        advised=False,
    ),
    PrintCase(
        "python library prints",
        "/tmp/fmt/src/ledger.py",
        "def post(entry):\n    print(entry)\n    return entry\n",
        advised=True,
    ),
    PrintCase(
        "go main package prints",
        "/tmp/fmt/cmd/tool/main.go",
        'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("done")\n}\n',
        advised=False,
    ),
    PrintCase(
        "go library prints",
        "/tmp/fmt/ledger/post.go",
        'package ledger\n\nimport "fmt"\n\nfunc Post(id int) {\n\tfmt.Println(id)\n}\n',
        advised=True,
    ),
    PrintCase(
        "node shebang script logs",
        "/tmp/fmt/bin/sync.js",
        "#!/usr/bin/env node\nconsole.log('synced');\n",
        advised=False,
    ),
    PrintCase(
        "breakpoint in an entry point stays blocked",
        "/tmp/fmt/tools/debug.py",
        'def main():\n    breakpoint()\n\n\nif __name__ == "__main__":\n    main()\n',
        advised=False,
        exit_code=2,
    ),
]


def failures() -> list[str]:
    found: list[str] = []
    for case in CASES:
        code, message = run_hook(HOOK, case.file_path, case.content)
        advised = "FMT-005" in message and "debug residue — confirm" in message
        if code != case.exit_code:
            found.append(f"{case.name}: expected exit {case.exit_code}, got {code}")
        if advised != case.advised:
            found.append(f"{case.name}: expected advised={case.advised}, got {advised}")
    return found


if __name__ == "__main__":
    sys.exit(report_failures("print-in-entry-points (FMT-005)", failures(), len(CASES)))
