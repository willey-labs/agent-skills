#!/usr/bin/env python3
"""Regression test — coding-standards config dotfile gating.

`.coding-standards-ignore` exemptions must each carry a `# reason: ...` (ISS-011);
without one the write blocks (an ungated ignore file is a self-exemption channel).
`.coding-standards-structure` stays structure-only (no comments / hooks: / toggles).

    python3 hooks/tests/test-config-dotfiles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, report  # noqa: E402

H = "block-structure-file-violations.py"
IGN = "/p/.coding-standards-ignore"
STR = "/p/.coding-standards-structure"

CASES: list[Case] = [
    # ISS-011 — ignore-file exemptions.
    Case("ignore pattern without reason blocks", H, IGN, "src/big-file.ts\n", block=True),
    Case("ignore pattern with reason passes", H, IGN,
         "src/big-file.ts  # reason: cohesive dispatch table, accepted in review F012\n", block=False),
    Case("ignore comments-only template passes", H, IGN,
         "# .coding-standards-ignore\n# src/legacy/** # reason: legacy\n", block=False),
    Case("ignore blank lines pass", H, IGN, "\n\n", block=False),
    # structure-file (regression — existing behavior).
    Case("structure comment blocks", H, STR, "follows: feature-first\n# essay\n", block=True),
    Case("structure toggle blocks", H, STR, "follows: x\ndeep-import: off\n", block=True),
    Case("structure clean passes", H, STR, "follows: feature-first\n", block=False),
]


if __name__ == "__main__":
    sys.exit(report("config-dotfiles", CASES))
