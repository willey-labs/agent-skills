#!/usr/bin/env python3
"""Interpreter-choice helpers for the hook wiring.

Which Python the PreToolUse hook commands run under, a one-line explanation of
that choice for the summary, and the project-scope mismatch warning. Split out of
settings.py (ST-008: one job per file) — settings.py owns the settings.json entry
and file I/O; this owns the interpreter decision.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def hook_interpreter(scope: str, python_command: str, venv_python: Path | None) -> str:
    """The interpreter string written into each hook command.

    A managed venv (created when the system Python is externally-managed) wins
    for both scopes — it's the only interpreter with the tree-sitter grammars.
    Otherwise project scope keeps the portable PATH name (`python3`) so the
    committed settings.json works on any teammate's machine; global scope pins
    the running interpreter's absolute path so the hooks can import the grammars
    pip installed into it (avoids the PATH-`python3`-vs-`sys.executable` mismatch
    that silently drops AST checks to regex).
    """
    if venv_python is not None:
        return str(venv_python)
    return python_command if scope == "project" else sys.executable


def interpreter_note(scope: str, venv_python: Path | None) -> str:
    """One line explaining why the hook commands use this interpreter."""
    if venv_python is not None:
        return "dedicated venv — pinned to this machine; re-run bootstrap per machine"
    if scope == "project":
        return "PATH name — portable across teammates"
    return "absolute path — pinned to this machine"


def warn_project_interpreter_mismatch(
    scope: str, report: dict, venv_python: Path | None
) -> None:
    """Warn when project-scope hooks may run under an interpreter lacking tree-sitter.

    Project hook commands use the portable PATH name; if that resolves to a
    different interpreter than the one tree-sitter was installed into, TS/JS AST
    checks silently fall back to regex. A managed venv (venv_python) sidesteps
    this, and global scope pins sys.executable — so neither needs the warning.
    """
    if scope != "project" or venv_python is not None or not report["packages_ok"]:
        return
    resolved = shutil.which(report["python_command"])
    try:
        same = resolved is not None and os.path.realpath(resolved) == os.path.realpath(sys.executable)
    except OSError:
        same = True
    if same:
        return
    print(
        f"  Note: project hook commands use '{report['python_command']}' "
        f"(resolves to {resolved or '(not found)'}), but tree-sitter is installed "
        f"in {sys.executable}. If these differ, TS/JS AST checks fall back to "
        f"regex — install tree-sitter into the PATH interpreter or run bootstrap "
        f"with it."
    )
