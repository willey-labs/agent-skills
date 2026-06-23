#!/usr/bin/env python3
"""Regression test — ST-005 structure-derived folder allowance (ISS-001).

A published catalog layout (bulletproof-react via `follows: feature-first` /
`route-colocated`) sanctions a `utils/` folder. The skill's own picker offers
those layouts, so a write into them must NOT be blocked once the structure is
recorded — while every other ST-005 case still blocks.

Needs an on-disk project root with a `.coding-standards-structure` file, so it
drives the hook directly rather than through harness.run_cases.

    python3 hooks/tests/test-structure-junk-folders.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "block-junk-paths.py"


def blocked(file_path: str) -> bool:
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": "export const x = 1\n"}}
    )
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)
    return proc.returncode == 2


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "package.json").write_text("{}\n")
        (root / "src" / "features" / "auth" / "utils").mkdir(parents=True)
        (root / "src" / "utils").mkdir(parents=True)
        (root / "src" / "helpers").mkdir(parents=True)
        structure = root / ".coding-standards-structure"
        feat_utils = str(root / "src/features/auth/utils/format-token.ts")
        src_utils = str(root / "src/utils/format-date.ts")
        src_helpers = str(root / "src/helpers/x.ts")
        utils_file = str(root / "src/feature/utils.ts")

        # No recorded structure → utils/ folders block.
        if not blocked(feat_utils):
            failures.append("no-structure: feature/utils should block")
        if not blocked(src_utils):
            failures.append("no-structure: src/utils should block")

        # follows: feature-first → utils/ folders allowed.
        structure.write_text("follows: feature-first\n")
        if blocked(feat_utils):
            failures.append("feature-first: feature/utils should pass")
        if blocked(src_utils):
            failures.append("feature-first: src/utils should pass")
        # ...but the allowance is narrow.
        if not blocked(src_helpers):
            failures.append("feature-first: helpers/ should still block")
        if not blocked(utils_file):
            failures.append("feature-first: utils.ts filename should still block")

        # A variant that does not publish utils/ → still blocks.
        structure.write_text("follows: feature-sliced-design\n")
        if not blocked(src_utils):
            failures.append("fsd: src/utils should still block")

    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print("ok — structure-junk-folder (ISS-001) cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
