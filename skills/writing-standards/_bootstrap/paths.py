#!/usr/bin/env python3
"""Filesystem paths shared across the _bootstrap package.

Anchored to the skill ROOT — the directory holding the `bootstrap.py` entry script
(one level ABOVE this package). Uses `.absolute()` not `.resolve()`: the skill is
symlinked from a canonical install location into `~/.claude/skills/<name>/` or
`<project>/.claude/skills/<name>/`. Resolving the symlink lands on the canonical
path, which has no `.claude` ancestor, breaking scope detection; we need the path
as the agent sees it, through the symlink.

CRITICAL: anchor to the MAIN script's invocation path (`bootstrap.py`), NOT this
module's own `__file__`. Python preserves the symlinked path for the main script
but RESOLVES the symlink for an imported module's `__file__` — which would land on
the canonical install path and break scope detection. See the same note in
coding-standards' _bootstrap/paths.py; this is a trimmed copy (no venv).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _invocation_path() -> Path:
    """The path bootstrap was started with, kept symlink-preserving.

    Anchors on `sys.argv[0]` (the path as typed), falling back to
    `__main__.__file__`. Absolute arg → use it verbatim. Relative arg → resolving
    via `os.getcwd()` drops the `.claude` shortcut, so prefer the shell's logical
    `$PWD` when it points at the same real file (guards a stale $PWD).
    """
    main = sys.modules.get("__main__")
    raw = sys.argv[0] or getattr(main, "__file__", None) or "bootstrap.py"
    path = Path(raw)
    if path.is_absolute():
        return path
    physical = Path(os.getcwd()) / raw
    pwd = os.environ.get("PWD")
    if pwd:
        logical = Path(pwd) / raw
        try:
            if logical.exists() and os.path.realpath(logical) == os.path.realpath(physical):
                return logical
        except OSError:
            return physical  # stale/unreadable $PWD — fall through to the physical path
    return physical


# The invoked bootstrap.py path, symlink-preserving — the anchor whose parents
# scope detection walks for `.claude`.
SCRIPT_PATH = _invocation_path().absolute()
# The skill root (bootstrap.py's directory), as seen through the install symlink.
SKILL_DIR = SCRIPT_PATH.parent
# Hooks dir resolved to its real location so settings.json command paths work from any cwd.
HOOKS_DIR = (SKILL_DIR / "hooks").resolve()
