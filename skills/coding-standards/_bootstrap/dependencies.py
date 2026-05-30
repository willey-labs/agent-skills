#!/usr/bin/env python3
"""The skill's third-party dependency registry and presence checks.

REQUIRED_PACKAGES is the single source of truth for the libraries the hooks
need to run. The readiness check (`_readiness`), the install flow (`_install`),
and the blocking gate (`bootstrap`) all iterate over it — nothing is
special-cased per library. To make a new library a hard requirement, add one
`(import_name, pip_name)` tuple below; everything else picks it up. (If it
needs a newer Python, bump MIN_PYTHON too.)

Stdlib-only deps (ast, re, json, …) and skill-internal modules (_exclusions,
_structure) are NOT listed — they're not installable and always present. System
tools the AGENT uses for review (git, gh) are out of scope: they aren't
pip-installable and live outside the hooks' runtime.

Currently: the tree-sitter grammars that back the FN-001 / FN-005 / OD-004 AST
checks on TypeScript/JavaScript.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .paths import MANAGED_VENV_DIR

# Minimum Python — the strictest floor across REQUIRED_PACKAGES. Today that's
# driven by tree-sitter: the current `tree-sitter` (>=0.24) and
# `tree-sitter-javascript` (>=0.24) wheels require Python >=3.10 (they dropped
# the cp39 wheel; only `tree-sitter-typescript` still ships one). On 3.9 a plain
# `pip install` resolves to stale grammars or fails outright, so 3.10 is the
# single floor: below it, bootstrap blocks rather than wiring hooks that can't
# run the required checks. If a future required package needs a higher Python,
# raise this.
MIN_PYTHON = (3, 10)

REQUIRED_PACKAGES = [
    ("tree_sitter", "tree-sitter"),
    ("tree_sitter_typescript", "tree-sitter-typescript"),
    ("tree_sitter_javascript", "tree-sitter-javascript"),
]


def managed_venv_python() -> Path:
    """Absolute path to the managed venv's interpreter (cross-platform)."""
    if os.name == "nt":
        return MANAGED_VENV_DIR / "Scripts" / "python.exe"
    return MANAGED_VENV_DIR / "bin" / "python"


def interpreter_has_packages(python_path: str) -> bool:
    """True if the interpreter at `python_path` can import every required package.

    Used to verify the interpreter the wired hooks actually run under (a missing
    or wiped dedicated venv must read as 'not available', not crash).
    """
    import_line = "import " + ", ".join(module for module, _package in REQUIRED_PACKAGES)
    try:
        subprocess.run(
            [python_path, "-c", import_line],
            check=True, capture_output=True, text=True, timeout=30,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def managed_venv_has_packages() -> bool:
    """True if the dedicated venv exists and can import every required package.

    This is the interpreter the hooks run under when the venv exists, so it — not
    the (often externally-managed) interpreter running bootstrap — is the one
    whose imports decide whether the required packages are really available.
    Cheap when no venv is present: the `.exists()` short-circuit avoids spawning
    a subprocess.
    """
    venv_python = managed_venv_python()
    if not venv_python.exists():
        return False
    return interpreter_has_packages(str(venv_python))


def check_required_packages() -> tuple[bool, list[str]]:
    """Detect whether every package in REQUIRED_PACKAGES is importable.

    Returns (all_present, missing_package_names). Checks the interpreter running
    bootstrap first, then the managed venv — the interpreter the hooks actually
    use when one exists (see `hook_interpreter`). Probing only the system Python
    made an externally-managed host (PEP 668) report 'missing' on every run even
    after a prior run had installed the packages into the venv, so each re-run
    pointlessly reinstalled and nagged for a session restart.
    """
    missing: list[str] = []
    for module, package in REQUIRED_PACKAGES:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if not missing:
        return True, []
    if managed_venv_has_packages():
        return True, []
    return False, missing


def required_packages_available(report: dict, venv_python: Path | None) -> bool:
    """True once every required package can actually be imported.

    A venv interpreter is only ever returned by `ensure_required_packages` when
    that venv has the packages, so its presence proves availability; otherwise
    the (possibly refreshed) report's `packages_ok` is authoritative.
    """
    if venv_python is not None:
        return True
    return report["packages_ok"]
