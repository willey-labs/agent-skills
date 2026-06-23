#!/usr/bin/env python3
"""Regression test — review-files.py finds the managed venv (P0).

review-files.py:resolve_interpreter once looked only at `<skill>/.venv`, but the
managed venv lives OUTSIDE the skill dir (ISS-006) at $CODING_STANDARDS_VENV /
$XDG_DATA_HOME/coding-standards/venv / ~/.local/share/coding-standards/venv. On a
PEP-668 host a review launched with a bare `python3` would then miss the grammars
and silently skip the TS/JS AST checks (FN-001 / OD-004 / precise FN-005),
reporting a file CLEAN. This pins that review-files.py's candidate venv dirs
include whatever `_bootstrap/paths.py:_managed_venv_dir` resolves to, so the two
can't drift apart again.

    python3 hooks/tests/test-review-files-venv.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent.parent  # skills/coding-standards
sys.path.insert(0, str(SKILL))
from _bootstrap.paths import _managed_venv_dir  # noqa: E402


def _load_review_files():
    spec = importlib.util.spec_from_file_location(
        "review_files", SKILL / "hooks" / "review-files.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    review = _load_review_files()
    failures: list[str] = []
    saved = {key: os.environ.get(key) for key in ("CODING_STANDARDS_VENV", "XDG_DATA_HOME")}

    def check(label: str, env: dict[str, str | None]) -> None:
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        # The bootstrap's resolved location must be one review-files.py looks in.
        bootstrap_dir = _managed_venv_dir()
        review_dirs = review._managed_venv_dirs()
        if bootstrap_dir not in review_dirs:
            failures.append(
                f"{label}: review-files misses managed venv {bootstrap_dir} "
                f"(checks {review_dirs})"
            )

    try:
        check("override", {"CODING_STANDARDS_VENV": "/tmp/cs-test-venv", "XDG_DATA_HOME": None})
        check("xdg", {"CODING_STANDARDS_VENV": None, "XDG_DATA_HOME": "/tmp/cs-xdg"})
        check("home-default", {"CODING_STANDARDS_VENV": None, "XDG_DATA_HOME": None})
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    print("ok — review-files managed-venv discovery (P0) cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
