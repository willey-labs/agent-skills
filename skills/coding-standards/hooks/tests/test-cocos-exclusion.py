#!/usr/bin/env python3
"""Regression test — root-anchored exclusion gated on Cocos layout (ISS-009).

`library/`, `temp/`, `settings/` at the project root are Cocos engine dirs and
are excluded — but ONLY for a Cocos-shaped project (a committed `assets/` dir at
root). A plain web/Django project with a root `settings/` must NOT lose
enforcement under it.

Needs an on-disk project root, so it drives the hook directly.

    python3 hooks/tests/test-cocos-exclusion.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK_PY = Path(__file__).resolve().parent.parent / "block-py-violations.py"
HOOK_TS = Path(__file__).resolve().parent.parent / "block-ts-violations.py"


def blocked(hook: Path, file_path: str, content: str) -> bool:
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}})
    return subprocess.run([sys.executable, str(hook)], input=payload,
                          capture_output=True, text=True).returncode == 2


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        # Non-Cocos project: root settings/ must still be enforced.
        nc = Path(d) / "web"
        (nc / "settings").mkdir(parents=True)
        (nc / "package.json").write_text("{}\n")
        if not blocked(HOOK_PY, str(nc / "settings" / "app.py"),
                       "from typing import Any\nx: dict[str, Any] = {}\n"):
            failures.append("non-Cocos: settings/app.py with Any should block")

        # Cocos project (has assets/): root settings/ is engine output, excluded.
        co = Path(d) / "game"
        (co / "settings").mkdir(parents=True)
        (co / "assets").mkdir(parents=True)
        (co / "package.json").write_text("{}\n")
        if blocked(HOOK_TS, str(co / "settings" / "app.ts"), "export const x: any = 1\n"):
            failures.append("Cocos: settings/app.ts should be excluded (pass)")

    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print("ok — cocos-exclusion (ISS-009) cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
