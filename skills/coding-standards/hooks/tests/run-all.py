#!/usr/bin/env python3
"""Run the whole hook regression suite with one command.

    python3 hooks/tests/run-all.py

Discovers every `test-*.py` sibling, runs each with the SAME interpreter, and
aggregates. Two distinct failure exits so green never hides a hole (ISS-028):

  exit 0  — all tests pass AND the tree-sitter AST path was exercisable.
  exit 1  — at least one test failed.
  exit 2  — tests passed but the AST backend is unavailable, so the AST-only
            checks (FN-001/FN-005/OD-004) were NOT exercised. Run this suite
            with the interpreter that has tree-sitter (the bootstrap venv).

Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
HOOKS_DIR = TESTS_DIR.parent
sys.path.insert(0, str(HOOKS_DIR))


def ast_backend_exercisable() -> bool:
    """True when the tree-sitter AST path can actually run under this interpreter."""
    try:
        from _ts_ast import ast_backend_available  # noqa: PLC0415

        return bool(ast_backend_available())
    except Exception:  # noqa: BLE001
        return False


def run_test_files() -> list[str]:
    """Run each test-*.py; return the names that failed."""
    failed: list[str] = []
    for test_file in sorted(TESTS_DIR.glob("test-*.py")):
        proc = subprocess.run([sys.executable, str(test_file)], capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        if proc.returncode != 0:
            failed.append(test_file.name)
    return failed


def main() -> int:
    failed = run_test_files()
    if failed:
        sys.stderr.write(f"\nSUITE FAIL — {len(failed)} file(s): {', '.join(failed)}\n")
        return 1
    if not ast_backend_exercisable():
        sys.stderr.write(
            "\nSUITE DEGRADED — all regex tests passed, but tree-sitter is unavailable "
            "under this interpreter, so the AST-only checks (FN-001/FN-005/OD-004) were "
            "NOT exercised. Re-run with the bootstrap venv python to test the real path.\n"
        )
        return 2
    print("\nSUITE OK — all tests pass and the AST path was exercised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
